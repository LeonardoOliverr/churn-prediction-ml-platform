"""
Factory da aplicação FastAPI.

Use create_app() para instanciar a aplicação — facilita testes de integração
que precisam de instâncias isoladas.
"""

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from domain.exceptions import (
    BatchTooLargeError,
    ModelNotFoundError,
    ProjectNotFoundError,
    TenantNotFoundError,
)
from src.config import get_settings
from src.middleware.logging import LoggingMiddleware
from src.middleware.rate_limit import key_limiter
from src.routers import admin, health, predict, predictions

logger = structlog.get_logger()

_DESCRIPTION = """
## Visão Geral

API de inferência multi-tenant para previsão de churn de clientes, construída sobre o
[IBM Telco Customer Churn Dataset](https://www.kaggle.com/datasets/yeanzc/telco-customer-churn-ibm-dataset/data).
Suporta múltiplos tenants e projetos com isolamento completo de dados, versionamento de
modelos via MLflow e log de predições por cliente.

---

## Autenticação

### Endpoints de inferência e histórico
Requerem **API Key** enviada no header `x-api-key`:
```
x-api-key: churn_live_sk_<secret>
```
A API key carrega o contexto de `tenant_id`, `project_id` e `scopes` — todo o isolamento
multi-tenant é derivado automaticamente dela.

### Endpoints de administração (`/admin/*`)
Requerem **JWT Bearer** no header `Authorization`:
```
Authorization: Bearer <token>
```
O token é gerado externamente com a chave `APP_SECRET_KEY` (HS256, expiração configurável).

---

## Resolução de Modelo (Champion-Challenger)

A API seleciona automaticamente o modelo operacional seguindo três níveis de especificidade:

| Nível | Fonte | Condição |
|---|---|---|
| 1 | `project_model_config` | Champion/challenger do projeto da API key |
| 2 | `project_model_config` | Champion ativo do tenant (API key sem `project_id`) |
| 3 | `churn.models` | Modelo global aprovado (`scope = 'global'`) |

Quando existe challenger ativo, o tráfego é dividido por hash determinístico de `customer_id`, respeitando `traffic_split`.
Se nenhum nível retornar resultado, a API responde `404 model_not_found`.

---

## Rate Limiting

| Escopo | Limite |
|---|---|
| Por API Key | 60 requisições / minuto |
| Por Tenant | 1.000 requisições / hora |

Requisições acima do limite retornam `429 Too Many Requests`.

---

## Códigos de Erro Comuns

| Código | `error` | Descrição |
|---|---|---|
| `401` | `unauthorized` | API key ausente, inválida ou revogada |
| `403` | `forbidden` | Escopo insuficiente para o endpoint |
| `404` | `model_not_found` | Nenhum modelo ativo encontrado para o tenant/projeto |
| `409` | `conflict` | Slug ou recurso já existe |
| `422` | `validation_error` | Payload inválido (campos faltantes ou fora do domínio) |
| `429` | `rate_limit_exceeded` | Limite de requisições atingido |
| `500` | `internal_error` | Erro interno do servidor |
"""

_TAGS_METADATA = [
    {
        "name": "health",
        "description": "**Probes de infraestrutura.** Utilizados por load balancers e orquestradores "
        "para verificar liveness e readiness da API.",
    },
    {
        "name": "inference",
        "description": "**Endpoints de inferência de churn.** Recebem features do cliente e retornam "
        "probabilidade de churn, nível de risco (`low` / `medium` / `high`) e metadados do modelo. "
        "Requerem API Key com escopo `predict`.",
    },
    {
        "name": "predictions",
        "description": "**Histórico de predições.** Consulta paginada das predições realizadas pelo "
        "tenant/projeto. O isolamento multi-tenant é garantido — não é possível acessar predições de "
        "outro tenant. Requer API Key com escopo `predict`.",
    },
    {
        "name": "admin",
        "description": "**Administração da plataforma.** Gerencia tenants, projetos, API keys e configuração "
        "champion/challenger de modelos. Requer JWT Bearer de admin. O `secret` de uma API key é retornado "
        "**apenas no momento da criação**.",
    },
]


def create_app() -> FastAPI:
    """Cria e configura a instância FastAPI com middlewares e routers."""
    _settings = get_settings()
    app = FastAPI(
        title="Churn Prediction API",
        description=_DESCRIPTION,
        version=_settings.app_version,
        contact={
            "name": "Plataforma ML — Suporte",
            "email": "ole071183@gmail.com",
        },
        license_info={
            "name": "MIT",
        },
        openapi_tags=_TAGS_METADATA,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Exception handlers de domínio
    @app.exception_handler(TenantNotFoundError)
    async def tenant_not_found_handler(request: Request, exc: TenantNotFoundError):
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "message": str(exc), "request_id": request_id},
        )

    @app.exception_handler(ProjectNotFoundError)
    async def project_not_found_handler(request: Request, exc: ProjectNotFoundError):
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "message": str(exc), "request_id": request_id},
        )

    @app.exception_handler(ModelNotFoundError)
    async def model_not_found_handler(request: Request, exc: ModelNotFoundError):
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=404,
            content={"error": "model_not_found", "message": str(exc), "request_id": request_id},
        )

    @app.exception_handler(BatchTooLargeError)
    async def batch_too_large_handler(request: Request, exc: BatchTooLargeError):
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=422,
            content={"error": "batch_too_large", "message": str(exc), "request_id": request_id},
        )

    # Rate limiting
    app.state.limiter = key_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # Logging estruturado
    app.add_middleware(LoggingMiddleware)

    # Routers
    app.include_router(health.router)
    app.include_router(predict.router)
    app.include_router(predictions.router)
    app.include_router(admin.router)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error("unhandled_exception", request_id=request_id, error=str(exc), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "Erro interno do servidor.",
                "request_id": request_id,
            },
        )

    return app


app = create_app()
