"""
Define o contrato declarativo de um modelo de ML para uso no pipeline unificado de treino.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from sklearn.base import BaseEstimator


@dataclass
class ModelSpec:
    name: str
    estimator_factory: Callable[..., BaseEstimator]
    default_params: dict[str, Any] = field(default_factory=dict)
    cli_overrides: dict[str, type] = field(default_factory=dict)
    experiment_suffix: str = ""
    log_feature_importances: bool = False
