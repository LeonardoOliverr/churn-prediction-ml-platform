"""
Endpoints de inferência de churn.

POST /predict       — predição para um único cliente
POST /predict/batch — predição em lote (máximo MAX_BATCH_SIZE clientes)

Ambos exigem autenticação via API key (x-api-key) com escopo 'predict'.
Rate limiting: 60 req/min por API key, 1000 req/hora por tenant.
"""

import time
import uuid

import pandas as pd
import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from sqlalchemy.engine import Connection

from domain.exceptions import BatchTooLargeError
from ml.config.settings import BOOL_FEATURES, CATEGORICAL_FEATURES, NUMERIC_FEATURES
from ml.domain.risk import classify_risk
from src.config import Settings, get_settings
from src.dependencies import _get_engine, get_db, require_scope
from src.middleware.auth import ApiKeyRecord
from src.middleware.rate_limit import key_limiter, tenant_limiter
from src.schemas.predict import (
    BatchPredictRequest,
    BatchPredictResponse,
    CustomerFeatures,
    PredictResponse,
)
from src.services.model_resolver import choose_for_customer, resolve_batch_models, resolve_model
from src.services.prediction_logger import log_prediction_bg

logger = structlog.get_logger()

router = APIRouter(tags=["inference"])

# Ordem das colunas que o pipeline sklearn espera (definida em ml/config.py)
_FEATURE_COLS = NUMERIC_FEATURES + BOOL_FEATURES + CATEGORICAL_FEATURES


def _build_dataframe(customers: list[CustomerFeatures]) -> pd.DataFrame:
    """Cria DataFrame com colunas na ordem exata exigida pelo ColumnTransformer."""
    rows = [c.model_dump(exclude={"customer_id"}) for c in customers]
    return pd.DataFrame(rows)[_FEATURE_COLS]


def _compute_shap(pipeline, X: pd.DataFrame, settings) -> list[dict] | None:
    """Computa SHAP para todas as linhas de X. Retorna None se desabilitado ou erro.

    XGBoost usa pred_contribs nativo (sem importar shap).
    RF e LR usam shap.TreeExplainer / LinearExplainer.
    """
    if not settings.shap_enabled:
        return None
    try:
        from ml.core.registry.mlflow import _get_feature_names
        from ml.explainability.shap_explainer import compute_shap_values

        preprocessor = pipeline.named_steps["preprocessor"]
        X_t = preprocessor.transform(X)
        if hasattr(X_t, "toarray"):
            X_t = X_t.toarray()

        feature_names = _get_feature_names(pipeline)
        return compute_shap_values(pipeline, X_t, feature_names, top_n=settings.shap_top_n)
    except Exception as exc:
        logger.warning("shap_computation_failed", error=str(exc))
        return None


def _make_response(
    customer: CustomerFeatures,
    prob: float,
    threshold: float,
    model_record: dict,
    prediction_id: str,
    explanation: dict | None = None,
) -> PredictResponse:
    """Monta PredictResponse a partir da probabilidade bruta do modelo."""
    return PredictResponse(
        prediction_id=prediction_id,
        customer_id=customer.customer_id,
        churn_probability=round(prob, 4),
        risk_level=classify_risk(prob),
        churn_pred=prob >= threshold,
        threshold_used=round(threshold, 3),
        model_version=str(model_record["version"]),
        model_name=str(model_record["name"]),
        model_id=str(model_record["id"]),
        explanation=explanation,
    )


_COMMON_RESPONSES = {
    401: {
        "description": "API key ausente, inválida ou revogada.",
        "content": {
            "application/json": {
                "example": {"error": "unauthorized", "message": "API key inválida ou revogada."}
            }
        },
    },
    403: {
        "description": "Escopo insuficiente para o endpoint.",
        "content": {
            "application/json": {
                "example": {"error": "forbidden", "message": "Escopo 'predict' requerido."}
            }
        },
    },
    404: {
        "description": "Nenhum modelo ativo encontrado para o tenant/projeto.",
        "content": {
            "application/json": {
                "example": {
                    "error": "model_not_found",
                    "message": "Nenhum modelo ativo encontrado para este tenant/projeto.",
                }
            }
        },
    },
    422: {
        "description": "Payload inválido — campo faltando ou fora do domínio esperado.",
    },
    429: {
        "description": "Limite de requisições atingido (60/min por key ou 1.000/h por tenant).",
        "content": {
            "application/json": {
                "example": {
                    "error": "rate_limit_exceeded",
                    "message": "Rate limit exceeded: 60 per 1 minute",
                }
            }
        },
    },
}


@router.post(
    "/predict",
    response_model=PredictResponse,
    summary="Predição individual",
    description="""
**Escopo requerido:** `predict` — enviar no header `x-api-key`.

---

Realiza a predição de churn para **um único cliente**.

O modelo ativo é selecionado a partir do `project_model_config` do projeto vinculado à API key.
Se o projeto não tiver um champion configurado, a API responde `404 model_not_found`.

Quando há challenger ativo no projeto, a seleção usa hash determinístico de `customer_id`
e respeita o `traffic_split` configurado.

O registro da predição em `churn.predictions` ocorre de forma **assíncrona** — não impacta a latência da resposta.
""",
    response_description="Probabilidade de churn, nível de risco (`low` / `medium` / `high`) e metadados do modelo.",
    responses=_COMMON_RESPONSES,
)
@key_limiter.limit("60/minute")
@tenant_limiter.limit("1000/hour")
def predict(
    request: Request,
    customer: CustomerFeatures,
    background_tasks: BackgroundTasks,
    db: Connection = Depends(get_db),
    api_key: ApiKeyRecord = Depends(require_scope("predict")),
    settings: Settings = Depends(get_settings),
    x_eval_batch_id: str | None = Header(default=None),
) -> PredictResponse:
    """Predição de churn para um único cliente."""
    request.state.tenant_id = api_key.tenant_id
    start_ms = time.perf_counter()

    pipeline, threshold, model_record = resolve_model(
        tenant_id=api_key.tenant_id,
        project_id=api_key.project_id,
        db=db,
        settings=settings,
        customer_id=customer.customer_id,
    )

    X = _build_dataframe([customer])
    prob = float(pipeline.predict_proba(X)[0, 1])

    shap_dicts = _compute_shap(pipeline, X, settings)
    explanation = shap_dicts[0] if shap_dicts else None

    latency_ms = round((time.perf_counter() - start_ms) * 1000)
    prediction_id = str(uuid.uuid4())

    background_tasks.add_task(
        log_prediction_bg,
        engine=_get_engine(settings),
        prediction_id=prediction_id,
        tenant_id=api_key.tenant_id,
        project_id=api_key.project_id or str(model_record.get("project_id", "")),
        customer_id=customer.customer_id,
        model_id=str(model_record["id"]),
        churn_prob=prob,
        churn_pred=prob >= threshold,
        threshold_used=threshold,
        latency_ms=latency_ms,
        eval_batch_id=x_eval_batch_id,
        shap_values=explanation,
    )

    return _make_response(customer, prob, threshold, model_record, prediction_id, explanation)


@router.post(
    "/predict/batch",
    response_model=BatchPredictResponse,
    summary="Predição em lote",
    description="""
**Escopo requerido:** `predict` — enviar no header `x-api-key`.

---

Realiza predições de churn para **múltiplos clientes** em uma única requisição.

- **Limite máximo:** 100 clientes por requisição (configurável via `MAX_BATCH_SIZE`)
- O modelo é resolvido por cliente para suportar roteamento champion/challenger
- As predições são registradas individualmente em `churn.predictions` de forma assíncrona
- Os resultados retornam na **mesma ordem** dos clientes enviados
""",
    response_description="Lista de predições na mesma ordem dos clientes enviados, com total processado.",
    responses={
        **_COMMON_RESPONSES,
        422: {
            "description": "Payload inválido, lote vazio ou acima do limite máximo.",
            "content": {
                "application/json": {
                    "examples": {
                        "batch_too_large": {
                            "summary": "Lote acima do limite",
                            "value": {
                                "error": "batch_too_large",
                                "message": "Máximo de 100 clientes por requisição.",
                            },
                        },
                        "empty_batch": {
                            "summary": "Lote vazio",
                            "value": {
                                "error": "empty_batch",
                                "message": "Lista de clientes não pode ser vazia.",
                            },
                        },
                    }
                }
            },
        },
    },
)
@key_limiter.limit("60/minute")
@tenant_limiter.limit("1000/hour")
def predict_batch(
    request: Request,
    batch: BatchPredictRequest,
    background_tasks: BackgroundTasks,
    db: Connection = Depends(get_db),
    api_key: ApiKeyRecord = Depends(require_scope("predict")),
    settings: Settings = Depends(get_settings),
    x_eval_batch_id: str | None = Header(default=None),
) -> BatchPredictResponse:
    """Predição em lote. Máximo de MAX_BATCH_SIZE clientes por requisição."""
    request.state.tenant_id = api_key.tenant_id

    if len(batch.customers) > settings.max_batch_size:
        raise BatchTooLargeError(received=len(batch.customers), limit=settings.max_batch_size)

    if not batch.customers:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "empty_batch",
                "message": "Lista de clientes não pode ser vazia.",
                "request_id": "unknown",
            },
        )

    start_ms = time.perf_counter()
    champion_loaded, challenger_loaded = resolve_batch_models(
        tenant_id=api_key.tenant_id,
        project_id=api_key.project_id,
        db=db,
        settings=settings,
    )

    grouped: dict[str, dict] = {}
    for index, customer in enumerate(batch.customers):
        pipeline, threshold, model_record = choose_for_customer(
            tenant_id=api_key.tenant_id,
            project_id=api_key.project_id,
            customer_id=customer.customer_id,
            champion_loaded=champion_loaded,
            challenger_loaded=challenger_loaded,
        )
        model_id = str(model_record["id"])
        if model_id not in grouped:
            grouped[model_id] = {
                "pipeline": pipeline,
                "threshold": threshold,
                "model_record": model_record,
                "items": [],
            }
        grouped[model_id]["items"].append((index, customer))

    results: list[PredictResponse | None] = [None] * len(batch.customers)
    engine = _get_engine(settings)
    for group in grouped.values():
        customers = [customer for _, customer in group["items"]]
        X = _build_dataframe(customers)
        probs = group["pipeline"].predict_proba(X)[:, 1]
        threshold = group["threshold"]
        model_record = group["model_record"]

        shap_dicts = _compute_shap(group["pipeline"], X, settings)

        for i, ((index, customer), prob) in enumerate(zip(group["items"], probs, strict=False)):
            prob = float(prob)
            explanation = shap_dicts[i] if shap_dicts else None
            latency_ms = round((time.perf_counter() - start_ms) * 1000)
            prediction_id = str(uuid.uuid4())
            results[index] = _make_response(
                customer, prob, threshold, model_record, prediction_id, explanation
            )
            background_tasks.add_task(
                log_prediction_bg,
                engine=engine,
                prediction_id=prediction_id,
                tenant_id=api_key.tenant_id,
                project_id=api_key.project_id or str(model_record.get("project_id", "")),
                customer_id=customer.customer_id,
                model_id=str(model_record["id"]),
                churn_prob=prob,
                churn_pred=prob >= threshold,
                threshold_used=threshold,
                latency_ms=latency_ms,
                eval_batch_id=x_eval_batch_id,
                shap_values=explanation,
            )

    latency_ms = round((time.perf_counter() - start_ms) * 1000)
    logger.info(
        "batch_predict", count=len(results), latency_ms=latency_ms, tenant_id=api_key.tenant_id
    )
    return BatchPredictResponse(
        results=[result for result in results if result is not None], total=len(results)
    )
