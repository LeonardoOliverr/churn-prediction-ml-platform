"""Constantes e enumerações canônicas do domínio de negócio.

Nenhum outro módulo do projeto deve redefinir estes valores como string literal solta.
"""

from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


RISK_THRESHOLD_LOW = 0.4  # prob < 0.4  → low
RISK_THRESHOLD_HIGH = 0.8  # prob >= 0.8 → high


class ModelRole(str, Enum):
    CHAMPION = "champion"
    CHALLENGER = "challenger"
    SHADOW = "shadow"


class ModelStatus(str, Enum):
    TRAINED = "trained"
    VALIDATED = "validated"
    APPROVED = "approved"
    ARCHIVED = "archived"


class CostModel(str, Enum):
    FLAT = "flat"
    CLTV = "cltv"
    MONTHLY_CHARGES = "monthly_charges"


class ApiScope(str, Enum):
    PREDICT = "predict"
    PREDICTIONS_READ = "predictions:read"


class EvaluationType(str, Enum):
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    MANUAL = "manual"
    BACKTEST = "backtest"
