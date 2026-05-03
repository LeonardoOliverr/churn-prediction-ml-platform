"""
Middleware de logging estruturado via structlog.

Registra cada request com método, path, status code, latência e request_id único.
O request_id é injetado no request.state para rastreabilidade nos handlers.
"""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware que loga todas as requests com request_id e latência."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = round((time.perf_counter() - start) * 1000)

        logger.info(
            "http_request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=latency_ms,
        )

        response.headers["X-Request-ID"] = request_id
        return response
