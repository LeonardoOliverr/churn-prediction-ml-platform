"""
Configurações da aplicação carregadas via variáveis de ambiente.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações globais da API. Todas as variáveis são obrigatórias em produção."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Banco de dados
    database_url: str

    # MLflow
    mlflow_tracking_uri: str

    # Autenticação
    app_secret_key: str
    jwt_expire_minutes: int = 30

    # Cache
    api_key_cache_ttl_seconds: int = 60
    model_cache_ttl_seconds: int = 300

    # Segurança
    bcrypt_rounds: int = 12

    # Inferência
    max_batch_size: int = 100

    # Explicabilidade SHAP
    shap_enabled: bool = False
    shap_top_n: int = 5

    # Logging
    log_level: str = "INFO"

    # Metadados da aplicação
    app_version: str = "1.0.0"


_settings: Settings | None = None


def get_settings() -> Settings:
    """Retorna instância singleton das configurações. Cria na primeira chamada."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
