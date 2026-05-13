"""Exceções de domínio de negócio.

Estas exceções representam erros de regra de negócio e devem ser lançadas
pelas camadas de serviço e ML. A conversão para respostas HTTP ocorre nos
exception handlers registrados em src/main.py.
"""


class DomainError(Exception):
    """Base para todas as exceções de domínio."""


class TenantNotFoundError(DomainError):
    def __init__(self, slug: str):
        super().__init__(f"Tenant não encontrado: {slug!r}")
        self.slug = slug


class ProjectNotFoundError(DomainError):
    def __init__(self, slug: str):
        super().__init__(f"Projeto não encontrado: {slug!r}")
        self.slug = slug


class ModelNotFoundError(DomainError):
    def __init__(self, detail: str = "Nenhum modelo ativo encontrado"):
        super().__init__(detail)


class InsufficientScopeError(DomainError):
    def __init__(self, required: str):
        super().__init__(f"Escopo insuficiente. Necessário: {required!r}")
        self.required = required


class CostConfigNotFoundError(DomainError):
    def __init__(self, tenant: str):
        super().__init__(f"cost_model_config não encontrado para tenant: {tenant!r}")
        self.tenant = tenant


class BatchTooLargeError(DomainError):
    def __init__(self, received: int, limit: int):
        super().__init__(f"Batch de {received} clientes excede o limite de {limit}.")
        self.received = received
        self.limit = limit


class InvalidThresholdError(DomainError):
    def __init__(self, value: float):
        super().__init__(f"Threshold inválido: {value}. Deve ser entre 0 e 1.")
        self.value = value
