"""Camada de domínio — fonte canônica de constantes e exceções de negócio.

Esta camada não importa nada de outros módulos do projeto.
"""

from domain.constants import (
    ApiScope,
    CostModel,
    EvaluationType,
    ModelRole,
    ModelStatus,
    RISK_THRESHOLD_HIGH,
    RISK_THRESHOLD_LOW,
    RiskLevel,
)
from domain.exceptions import (
    BatchTooLargeError,
    CostConfigNotFoundError,
    DomainError,
    InsufficientScopeError,
    InvalidThresholdError,
    ModelNotFoundError,
    ProjectNotFoundError,
    TenantNotFoundError,
)

__all__ = [
    "ApiScope",
    "BatchTooLargeError",
    "CostConfigNotFoundError",
    "CostModel",
    "DomainError",
    "EvaluationType",
    "InsufficientScopeError",
    "InvalidThresholdError",
    "ModelNotFoundError",
    "ModelRole",
    "ModelStatus",
    "ProjectNotFoundError",
    "RISK_THRESHOLD_HIGH",
    "RISK_THRESHOLD_LOW",
    "RiskLevel",
    "TenantNotFoundError",
]
