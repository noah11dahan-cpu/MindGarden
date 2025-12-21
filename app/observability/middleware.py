import logging
import time
from typing import Any, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


logger = logging.getLogger("mindgarden.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs one line per request with latency and (when available) user_id."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        start = time.perf_counter()
        response: Response | None = None
        status_code: int = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            user_id = getattr(request.state, "user_id", None)

            # Use logger "extra" so our formatter can render structured fields.
            logger.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "user_id": user_id,
                },
            )
