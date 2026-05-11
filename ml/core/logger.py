"""Re-exporta get_logger do core compartilhado da plataforma.

A implementação vive em core.logger para ser acessível a pipeline/, scripts/ e ml/
sem criar dependência cruzada entre módulos.
"""

from core.logger import get_logger  # noqa: F401
