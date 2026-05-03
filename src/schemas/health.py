"""
Schemas dos endpoints de health check.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class CheckResult(BaseModel):
    """Resultado de um check de dependência individual."""

    model_config = ConfigDict(json_schema_extra={"example": {"status": "ok", "latency_ms": 4}})

    status: Literal["ok", "error"]
    latency_ms: Optional[int] = Field(None, description="Latência da verificação em milissegundos. `null` se o check falhou antes de completar.")


class LivenessResponse(BaseModel):
    """Resposta do liveness probe."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "version": "1.0.0",
                "timestamp": "2026-05-02T14:23:11.123456Z",
                "latency_ms": 1,
            }
        }
    )

    status: Literal["ok"]
    version: str = Field(..., description="Versão da API.")
    timestamp: str = Field(..., description="Timestamp UTC do momento da resposta (ISO 8601).")
    latency_ms: int = Field(..., description="Latência de processamento do próprio endpoint em milissegundos.")


class ReadinessResponse(BaseModel):
    """Resposta do readiness probe com resultado de cada dependência."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ready",
                "timestamp": "2026-05-02T14:23:11.123456Z",
                "checks": {
                    "database": {"status": "ok", "latency_ms": 3},
                    "mlflow": {"status": "ok", "latency_ms": 11},
                },
            }
        }
    )

    status: Literal["ready", "degraded"] = Field(
        ...,
        description='`ready` — todas as dependências operacionais. `degraded` — uma ou mais dependências com falha.',
    )
    timestamp: str = Field(..., description="Timestamp UTC do momento da verificação (ISO 8601).")
    checks: dict[str, CheckResult] = Field(..., description="Resultado individual de cada dependência verificada.")
