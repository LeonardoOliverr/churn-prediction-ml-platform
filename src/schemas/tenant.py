"""
Schemas dos endpoints de administração (tenants, projetos e API keys).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from domain.constants import ApiScope, ModelRole


class TenantCreate(BaseModel):
    """Payload para criação de tenant."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"name": "IBM Telco", "slug": "ibm-telco"}}
    )

    name: str = Field(..., description="Nome de exibição do tenant.")
    slug: str = Field(
        ..., description="Identificador único em lowercase-kebab. Imutável após criação."
    )


class TenantResponse(BaseModel):
    """Resposta após criação de tenant."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "name": "IBM Telco",
                "slug": "ibm-telco",
            }
        }
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
    project_id: str | None = Field(
        None,
        description="UUID do projeto. Se omitido, a key tem escopo de tenant e usa o nível 2 da cascade de modelo.",
    )
    scopes: list[ApiScope] = Field(
        [ApiScope.PREDICT],
        description=(
            "Escopos concedidos à key. Uma key pode ter um ou mais escopos simultaneamente.\n\n"
            "| Escopo | Endpoints liberados |\n"
            "|---|---|\n"
            "| `predict` | `POST /predict`, `POST /predict/batch` |\n"
            "| `predictions:read` | `GET /predictions` |"
        ),
    )
    description: str | None = Field(None, description="Descrição livre para identificação da key.")
    expires_at: datetime | None = Field(
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
    key_prefix: str = Field(
        ..., description="Prefixo público da key (usado para identificação em logs)."
    )
    secret: str = Field(
        ..., description="Key completa — **retornada apenas uma vez**. Não é possível recuperá-la."
    )
    tenant_id: str
    project_id: str | None
    scopes: list[str]
    expires_at: datetime | None = Field(
        None, description="Data/hora de expiração. `null` = sem expiração."
    )


class ApiKeyRecord(BaseModel):
    """Registro de API key para listagem (sem o secret)."""

    id: str = Field(..., description="UUID da API key.")
    key_prefix: str = Field(..., description="Prefixo público da key.")
    tenant_id: str
    project_id: str | None
    scopes: list[str]
    is_active: bool = Field(..., description="`false` indica que a key foi revogada.")
    created_at: str
    expires_at: str | None = Field(
        None, description="Data/hora de expiração. `null` = sem expiração."
    )
    last_used_at: str | None = Field(
        None, description="Última vez que a key foi utilizada. `null` se nunca usada."
    )


class ChampionModelConfigure(BaseModel):
    """Payload para ativar ou trocar o champion de um tenant ou projeto."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "threshold": 0.5,
                "activation_reason": "baseline aprovado para producao",
                "description": "Logistic Regression v1",
            }
        }
    )

    model_id: str = Field(..., description="UUID do modelo em churn.models.")
    threshold: float = Field(0.5, ge=0, le=1, description="Threshold operacional do modelo.")
    activation_reason: str | None = Field(None, description="Motivo para ativar esta configuracao.")
    description: str | None = Field(
        None, description="Descricao livre da configuracao operacional."
    )


class ChallengerModelConfigure(ChampionModelConfigure):
    """Payload para ativar ou trocar o challenger de um tenant ou projeto."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "threshold": 0.5,
                "traffic_split": 0.2,
                "activation_reason": "teste controlado com Random Forest",
                "description": "Random Forest v2",
            }
        }
    )

    traffic_split: float = Field(
        ..., gt=0, le=0.5, description="Fracao do trafego enviada ao challenger."
    )


class ModelPromotionRequest(BaseModel):
    """Payload para promover um challenger a champion."""

    activation_reason: str | None = Field(None, description="Motivo da promocao do challenger.")


class ModelDeactivationRequest(BaseModel):
    """Payload para desligar uma configuracao de producao."""

    reason: str = Field(..., description="Motivo operacional do desligamento.")
    replacement_model_id: str | None = Field(
        None, description="Modelo substituto quando o desligamento for do champion."
    )


class ProjectModelConfigRecord(BaseModel):
    """Registro operacional de modelo configurado para um tenant ou projeto."""

    id: str
    tenant_id: str
    project_id: str | None
    model_id: str
    model_name: str
    model_version: str
    model_status: str
    role: ModelRole
    threshold: float
    traffic_split: float
    is_active: bool
    environment: str
    configured_by: str | None = None
    description: str | None = None
    activation_reason: str | None = None
    configured_at: str
    deactivated_at: str | None = None
    created_at: str
    updated_at: str


class ProjectModelConfigResponse(BaseModel):
    """Resposta apos operacao administrativa em project_model_config."""

    config: ProjectModelConfigRecord


class ProjectModelConfigListResponse(BaseModel):
    """Listagem de configuracoes champion/challenger de um tenant ou projeto."""

    champion: ProjectModelConfigRecord | None
    challenger: ProjectModelConfigRecord | None
    history: list[ProjectModelConfigRecord]
