"""
Configuração de rate limiting via slowapi.

key_limiter    — limita por API key individual (x-api-key header)
tenant_limiter — limita por tenant_id, agregando todas as keys do tenant

O SlowAPIMiddleware executa antes das dependências FastAPI, então
request.state.tenant_id ainda não está disponível quando as key functions
são chamadas. A solução é manter _prefix_tenant_cache (prefix → tenant_id),
populado por src.dependencies após a primeira autenticação bem-sucedida.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# prefix (primeiros 20 chars da key) → tenant_id
# Populado por src.dependencies.get_current_api_key após auth bem-sucedida.
# Dict simples: o número de prefixos únicos é pequeno e não expira
# (prefix é imutável — mesmo após revogação, o mapping é inócuo).
_prefix_tenant_cache: dict[str, str] = {}


def _get_api_key(request) -> str:
    """Extrai API key do header para uso como chave de rate limiting."""
    return request.headers.get("x-api-key") or get_remote_address(request)


def _get_tenant_id(request) -> str:
    """Resolve tenant_id via prefix cache para rate limiting agregado por tenant."""
    api_key = request.headers.get("x-api-key", "")
    if len(api_key) >= 20:
        tenant_id = _prefix_tenant_cache.get(api_key[:20])
        if tenant_id:
            return tenant_id
    return get_remote_address(request)


key_limiter = Limiter(key_func=_get_api_key)
tenant_limiter = Limiter(key_func=_get_tenant_id)
