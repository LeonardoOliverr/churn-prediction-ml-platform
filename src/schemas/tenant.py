"""
Schemas dos endpoints de administração (tenants, projetos e API keys).
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Scope(str, Enum):
    predict = "predict"
    predictions_read = "predictions:read"


class TenantCreate(BaseModel):
    """Payload para criação de tenant."""

    model_config = ConfigDict(json_schema_extra={"example": {"name": "IBM Telco", "slug": "ibm-telco"}})

    name: str = Field(..., description="Nome de exibição do tenant.")
    slug: str = Field(..., description="Identificador único em lowercase-kebab. Imutável após criação.")


class TenantResponse(BaseModel):
    """Resposta após criação de tenant."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", "name": "IBM Telco", "slug": "ibm-telco"}}
    )

    id: str = Field(..., description="UUID do tenant.")
    name: str
    slug: str


class ProjectCreate(BaseModel):
    """Payload para criação de projeto dentro de um tenant."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenant_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "name": "Telco Churn 2018",
                "slug": "telco-churn-2018",
            }
        }
    )

    tenant_id: str = Field(..., description="UUID do tenant ao qual o projeto pertence.")
    name: str = Field(..., description="Nome de exibição do projeto.")
    slug: str = Field(..., description="Identificador único dentro do tenant (lowercase-kebab).")


class ProjectResponse(BaseModel):
    """Resposta após criação de projeto."""

    id: str = Field(..., description="UUID do projeto.")
    tenant_id: str
    name: str
    slug: str


class ApiKeyCreate(BaseModel):
    """Payload para geração de API key."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenant_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "project_id": "9b2e1f3a-4c8d-4e1b-b5a7-1f2e3d4c5b6a",
                "scopes": ["predict", "predictions:read"],
                "description": "Key de produção — sistema CRM",
                "expires_at": "2026-12-31T23:59:59Z",
            }
        }
    )

    tenant_id: str = Field(..., description="UUID do tenant proprietário desta key.")
    project_id: Optional[str] = Field(
        None,
        description="UUID do projeto. Se omitido, a key tem escopo de tenant e usa o nível 2 da cascade de modelo.",
    )
    scopes: list[Scope] = Field(
        [Scope.predict],
        description=(
            "Escopos concedidos à key. Uma key pode ter um ou mais escopos simultaneamente.\n\n"
            "| Escopo | Endpoints liberados |\n"
            "|---|---|\n"
            "| `predict` | `POST /predict`, `POST /predict/batch` |\n"
            "| `predictions:read` | `GET /predictions` |"
        ),
    )
    description: Optional[str] = Field(None, description="Descrição livre para identificação da key.")
    expires_at: Optional[datetime] = Field(
        None,
        description="Data/hora de expiração da key (ISO 8601). `null` = sem expiração.",
    )


class ApiKeyResponse(BaseModel):
    """Resposta após geração de API key. O `secret` é retornado **apenas nesta resposta** — armazene-o com segurança."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                "key_prefix": "churn_live_sk_Xm3P",
                "secret": "churn_live_sk_Xm3P9vKqLzR2wBnT...",
                "tenant_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "project_id": "9b2e1f3a-4c8d-4e1b-b5a7-1f2e3d4c5b6a",
                "scopes": ["predict"],
                "expires_at": "2026-12-31T23:59:59+00:00",
            }
        }
    )

    id: str = Field(..., description="UUID da API key.")
    key_prefix: str = Field(..., description="Prefixo público da key (usado para identificação em logs).")
    secret: str = Field(..., description="Key completa — **retornada apenas uma vez**. Não é possível recuperá-la.")
    tenant_id: str
    project_id: Optional[str]
    scopes: list[str]
    expires_at: Optional[datetime] = Field(None, description="Data/hora de expiração. `null` = sem expiração.")


class ApiKeyRecord(BaseModel):
    """Registro de API key para listagem (sem o secret)."""

    id: str = Field(..., description="UUID da API key.")
    key_prefix: str = Field(..., description="Prefixo público da key.")
    tenant_id: str
    project_id: Optional[str]
    scopes: list[str]
    is_active: bool = Field(..., description="`false` indica que a key foi revogada.")
    created_at: str
    expires_at: Optional[str] = Field(None, description="Data/hora de expiração. `null` = sem expiração.")
    last_used_at: Optional[str] = Field(None, description="Última vez que a key foi utilizada. `null` se nunca usada.")
