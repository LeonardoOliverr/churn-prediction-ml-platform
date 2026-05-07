"""Configuração centralizada de logging estruturado para o módulo ml."""

from __future__ import annotations

import logging
import os
import sys
import warnings

import structlog

# Suprime warnings verbosos de bibliotecas externas que poluem o output
warnings.filterwarnings("ignore", category=UserWarning, module="mlflow")


def _wrap_console_renderer(base: structlog.types.Processor) -> structlog.types.Processor:
    """Envolve o ConsoleRenderer para expandir o campo 'report' com quebras de linha reais.

    Campos 'report' passados como kwarg ao logger seriam escapados pelo renderer padrão
    (ex: '\\n' em vez de nova linha). Este wrapper extrai o campo antes da renderização
    e o anexa ao output com newlines reais — sem usar print(), mantendo o padrão estruturado.
    No renderer JSON (sem TTY) o campo permanece no event_dict para ser serializado normalmente.
    """

    def _renderer(
        logger: object,
        method: str,
        event_dict: structlog.types.EventDict,
    ) -> str:
        report: str | None = event_dict.pop("report", None)
        result: str = base(logger, method, event_dict)  # type: ignore[arg-type]
        if report:
            return f"{result}\n{report}"
        return result

    return _renderer


def _configure() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    # ConsoleRenderer com cores no terminal; JSON puro no Docker (sem TTY)
    if sys.stdout.isatty():
        renderer: structlog.types.Processor = _wrap_console_renderer(
            structlog.dev.ConsoleRenderer()
        )
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
    )


_configure()


def get_logger() -> structlog.BoundLogger:
    return structlog.get_logger()
