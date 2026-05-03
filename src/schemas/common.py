"""
Schemas compartilhados entre múltiplos endpoints.
"""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Resposta de erro padronizada."""

    error: str
    message: str
    request_id: str
