"""Compatibility wrapper for preprocessing now stored in ml.data.preprocessing."""

from ml.data.preprocessing import (
    _build_engine,
    _resolve_project_id,
    _resolve_tenant_id,
    build_preprocessor,
    load_data,
)

__all__ = [
    "_build_engine",
    "_resolve_project_id",
    "_resolve_tenant_id",
    "build_preprocessor",
    "load_data",
]
