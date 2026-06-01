"""
Endpoint de histórico de predições.

GET /predictions — retorna predições paginadas do tenant/projeto da API key.
"""

import structlog
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.dependencies import get_db, require_scope
from src.middleware.auth import ApiKeyRecord
from src.schemas.predict import ExplainResponse, PredictionRecord, PredictionsListResponse
from src.services.explanation_service import get_explanation

logger = structlog.get_logger()

router = APIRouter(tags=["predictions"])


@router.get(
    "/predictions",
    response_model=PredictionsListResponse,
    summary="Histórico de predições",
    description="""
**Escopo requerido:** `predictions:read` — enviar no header `x-api-key`.

---

Retorna o histórico **paginado** de predições realizadas pelo tenant/projeto da API Key.

- O escopo de dados é determinado automaticamente pela API Key (`tenant_id` + `project_id`)
- Isolamento multi-tenant garantido — não é possível acessar predições de outro tenant
- Ordenação: predições mais recentes primeiro

**Parâmetros de paginação:**
- `page` — número da página (padrão: `1`)
- `page_size` — itens por página, de 1 a 100 (padrão: `20`)
""",
    response_description="Lista paginada de predições com total de registros.",
    responses={
        401: {
            "description": "API key ausente, inválida ou revogada.",
            "content": {
                "application/json": {
                    "example": {"error": "unauthorized", "message": "API key inválida ou revogada."}
                }
            },
        },
        403: {
            "description": "Escopo insuficiente.",
            "content": {
                "application/json": {
                    "example": {
                        "error": "forbidden",
                        "message": "Escopo 'predictions:read' requerido.",
                    }
                }
            },
        },
    },
)
def list_predictions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Connection = Depends(get_db),
    api_key: ApiKeyRecord = Depends(require_scope("predictions:read")),
) -> PredictionsListResponse:
    """Retorna predições paginadas filtradas por tenant e projeto."""
    offset = (page - 1) * page_size

    filters = {"tenant_id": api_key.tenant_id}
    project_filter = ""
    if api_key.project_id:
        project_filter = "AND project_id = :project_id"
        filters["project_id"] = api_key.project_id

    rows = (
        db.execute(
            text(f"""
            SELECT id, customer_id, churn_prob AS churn_probability, churn_pred,
                   threshold_used, latency_ms, requested_at, model_id
            FROM churn.predictions
            WHERE tenant_id = :tenant_id
            {project_filter}
            ORDER BY requested_at DESC
            LIMIT :limit OFFSET :offset
        """),
            {**filters, "limit": page_size, "offset": offset},
        )
        .mappings()
        .all()
    )

    total_row = (
        db.execute(
            text(f"""
            SELECT COUNT(*) AS total
            FROM churn.predictions
            WHERE tenant_id = :tenant_id
            {project_filter}
        """),
            filters,
        )
        .mappings()
        .first()
    )

    items = [
        PredictionRecord(
            id=str(r["id"]),
            customer_id=r["customer_id"],
            churn_probability=float(r["churn_probability"]),
            churn_pred=bool(r["churn_pred"]),
            threshold_used=float(r["threshold_used"]),
            latency_ms=r["latency_ms"],
            requested_at=str(r["requested_at"]),
            model_id=str(r["model_id"]),
        )
        for r in rows
    ]

    return PredictionsListResponse(
        items=items,
        total=int(total_row["total"]),
        page=page,
        page_size=page_size,
    )


@router.get(
    "/predictions/{prediction_id}/explain",
    response_model=ExplainResponse,
    summary="Explicação LLM de uma predição",
    description="""
**Escopo requerido:** `predictions:read` — enviar no header `x-api-key`.

---

Retorna a explicação em linguagem natural para os valores SHAP de uma predição específica.

**Comportamento de cache:** a explicação é gerada pelo LLM **apenas na primeira chamada**.
Chamadas subsequentes para o mesmo `prediction_id` retornam o texto já gravado no banco
(`cached: true`) com latência próxima de zero.

**Pré-condições para geração:**
- SHAP deve ter sido calculado para esta predição (`shap_values` não nulo)
- O projeto deve ter tradução LLM habilitada (`project_llm_config.enabled = true`)
- `OPENAI_API_KEY` deve estar definida no ambiente

Em qualquer outro caso, `explanation_text` é retornado como `null` com `HTTP 200`.
""",
    responses={
        401: {
            "description": "API key ausente ou inválida.",
            "content": {
                "application/json": {
                    "example": {"error": "unauthorized", "message": "API key inválida ou revogada."}
                }
            },
        },
        404: {
            "description": "Predição não encontrada no tenant/projeto da API key.",
            "content": {
                "application/json": {
                    "example": {
                        "error": "not_found",
                        "message": "Predição 'abc123' não encontrada.",
                    }
                }
            },
        },
    },
)
def explain_prediction(
    prediction_id: str = Path(..., description="UUID da predição a ser explicada."),
    db: Connection = Depends(get_db),
    api_key: ApiKeyRecord = Depends(require_scope("predictions:read")),
) -> ExplainResponse:
    """Retorna ou gera a explicação LLM para os valores SHAP de uma predição."""
    return get_explanation(
        prediction_id=prediction_id,
        tenant_id=api_key.tenant_id,
        db=db,
    )
