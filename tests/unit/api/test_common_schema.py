"""
Testes de smoke para src/schemas/common.py.

Garante que ErrorResponse pode ser instanciado e serializado corretamente.
"""

from src.schemas.common import ErrorResponse


def test_error_response_instantiation():
    """ErrorResponse pode ser criado com os três campos obrigatórios."""
    err = ErrorResponse(
        error="not_found",
        message="Recurso não encontrado.",
        request_id="req-abc-123",
    )
    assert err.error == "not_found"
    assert err.message == "Recurso não encontrado."
    assert err.request_id == "req-abc-123"


def test_error_response_serializes_to_dict():
    """model_dump() retorna os campos esperados."""
    err = ErrorResponse(error="internal_error", message="Erro.", request_id="req-xyz")
    data = err.model_dump()
    assert set(data.keys()) == {"error", "message", "request_id"}
