"""
Testes unitários dos endpoints administrativos de configuração de modelos.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from src.routers import admin
from src.schemas.tenant import ChallengerModelConfigure, ModelDeactivationRequest


def test_validate_model_for_project_accepts_global_approved_model():
    """Modelo global approved é elegível para qualquer projeto."""
    project = {"id": "project-1", "tenant_id": "tenant-1"}
    model = {
        "id": "model-1",
        "tenant_id": None,
        "project_id": None,
        "scope": "global",
        "status": "approved",
    }

    with patch("src.routers.admin._get_model", return_value=model):
        assert admin._validate_model_for_project(MagicMock(), project, "model-1") == model


def test_validate_model_for_project_rejects_not_approved_model():
    """Modelo sem status approved não pode ser configurado em produção."""
    project = {"id": "project-1", "tenant_id": "tenant-1"}
    model = {
        "id": "model-1",
        "tenant_id": None,
        "project_id": None,
        "scope": "global",
        "status": "validated",
    }

    with patch("src.routers.admin._get_model", return_value=model):
        with pytest.raises(HTTPException) as exc:
            admin._validate_model_for_project(MagicMock(), project, "model-1")

    assert exc.value.status_code == 409


def test_configure_challenger_rejects_active_champion_as_challenger():
    """O mesmo modelo não pode ser champion e challenger ativo ao mesmo tempo."""
    payload = ChallengerModelConfigure(model_id="model-1", threshold=0.5, traffic_split=0.2)
    claims = SimpleNamespace(sub="admin-1")

    with (
        patch(
            "src.routers.admin._get_project",
            return_value={"id": "project-1", "tenant_id": "tenant-1"},
        ),
        patch("src.routers.admin._validate_model_for_scope"),
        patch(
            "src.routers.admin._active_config_by_model",
            return_value={"id": "cfg-1", "role": "champion"},
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            admin.configure_challenger("project-1", payload, MagicMock(), claims)

    assert exc.value.status_code == 409


def test_deactivate_champion_without_replacement_returns_conflict():
    """Champion não pode ser desligado sem modelo substituto."""
    payload = ModelDeactivationRequest(reason="rollback", replacement_model_id=None)
    claims = SimpleNamespace(sub="admin-1")

    with (
        patch(
            "src.routers.admin._get_project",
            return_value={"id": "project-1", "tenant_id": "tenant-1"},
        ),
        patch(
            "src.routers.admin._active_config_by_model",
            return_value={"id": "cfg-1", "role": "champion"},
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            admin.deactivate_model_config("project-1", "model-1", payload, MagicMock(), claims)

    assert exc.value.status_code == 409
