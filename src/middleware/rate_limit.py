"""
Configuração de rate limiting via slowapi.

key_limiter   — limita por API key (x-api-key header)
tenant_limiter — limita por tenant_id (injetado no request.state)
"""

from slowapi import Limiter
from slowapi.util import get_remote_address


def _get_api_key(request) -> str:
    """Extrai API key do header para uso como chave de rate limiting."""
    return request.headers.get("x-api-key") or get_remote_address(request)


def _get_tenant_id(request) -> str:
    """Extrai tenant_id do request.state para rate limiting por tenant."""
    return getattr(request.state, "tenant_id", None) or get_remote_address(request)


key_limiter = Limiter(key_func=_get_api_key)
tenant_limiter = Limiter(key_func=_get_tenant_id)
