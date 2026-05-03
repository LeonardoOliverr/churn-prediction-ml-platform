"""
Endpoints de health check.

GET /health       — liveness probe (sempre 200)
GET /health/ready — readiness probe (verifica banco e MLflow, retorna latências)
"""

import time
import urllib.request
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.config import Settings, get_settings
from src.dependencies import get_db
from src.schemas.health import CheckResult, LivenessResponse, ReadinessResponse

logger = structlog.get_logger()

router = APIRouter(tags=["health"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _check_database(db: Connection) -> CheckResult:
    start = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        return CheckResult(status="ok", latency_ms=round((time.perf_counter() - start) * 1000))
    except Exception as exc:
        logger.error("health_check_database_failed", error=str(exc))
        return CheckResult(status="error", latency_ms=None)


def _check_mlflow(tracking_uri: str) -> CheckResult:
    start = time.perf_counter()
    try:
        url = tracking_uri.rstrip("/") + "/health"
        req = urllib.request.urlopen(url, timeout=3)
        req.close()
        return CheckResult(status="ok", latency_ms=round((time.perf_counter() - start) * 1000))
    except Exception as exc:
        logger.error("health_check_mlflow_failed", error=str(exc))
        return CheckResult(status="error", latency_ms=None)


@router.get(
    "/health",
    response_model=LivenessResponse,
    summary="Liveness probe",
    description="Indica que o processo está ativo. Sempre retorna `200 OK` enquanto o processo estiver rodando. "
    "Utilizado por load balancers e orquestradores (Kubernetes, ECS) para detectar falhas de processo. "
    "Não verifica dependências externas — use `/health/ready` para isso.",
    response_description="Processo ativo, versão da API e timestamp UTC.",
)
def health(settings: Settings = Depends(get_settings)) -> LivenessResponse:
    """Liveness probe. Sempre retorna 200 enquanto o processo estiver ativo."""
    start = time.perf_counter()
    return LivenessResponse(
        status="ok",
        version=settings.app_version,
        timestamp=_now_iso(),
        latency_ms=round((time.perf_counter() - start) * 1000),
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="""
Verifica se a API está pronta para receber tráfego, testando a conectividade com todas as dependências críticas.

**Dependências verificadas:**
- `database` — PostgreSQL: executa `SELECT 1` e mede latência
- `mlflow` — MLflow Tracking Server: verifica endpoint `/health` e mede latência

**Comportamento:**
- `200 ready` — todas as dependências operacionais
- `503 degraded` — uma ou mais dependências com falha

Use este endpoint como **readiness probe** em orquestradores — o tráfego só deve ser roteado para instâncias `ready`.
""",
    response_description="Status de cada dependência com latência individual.",
    responses={
        503: {
            "description": "Uma ou mais dependências críticas indisponíveis.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "degraded",
                        "timestamp": "2026-05-02T14:23:11.123456Z",
                        "checks": {
                            "database": {"status": "error", "latency_ms": None},
                            "mlflow": {"status": "ok", "latency_ms": 11},
                        },
                    }
                }
            },
        }
    },
)
def health_ready(
    db: Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """Readiness probe. Verifica banco e MLflow, retorna latências individuais."""
    checks = {
        "database": _check_database(db),
        "mlflow": _check_mlflow(settings.mlflow_tracking_uri),
    }

    overall = "ready" if all(c.status == "ok" for c in checks.values()) else "degraded"
    status_code = 200 if overall == "ready" else 503

    body = ReadinessResponse(
        status=overall,
        timestamp=_now_iso(),
        checks=checks,
    )

    logger.info("readiness_check", status=overall, checks={k: v.status for k, v in checks.items()})

    return JSONResponse(status_code=status_code, content=body.model_dump())
