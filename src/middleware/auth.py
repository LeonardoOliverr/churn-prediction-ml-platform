"""
Dataclasses que representam o contexto de autenticação injetado nas requests.

A lógica de validação fica em src/dependencies.py para aproveitar o sistema
de Depends do FastAPI. Este módulo expõe apenas os tipos compartilhados.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ApiKeyRecord:
    """Contexto de autenticação resolvido a partir de uma API key válida."""

    id: str
    tenant_id: str
    project_id: Optional[str]
    scopes: list[str]
    key_prefix: str


@dataclass
class AdminClaims:
    """Claims extraídos e validados de um JWT de admin."""

    sub: str
    exp: int
    extra: dict = field(default_factory=dict)
