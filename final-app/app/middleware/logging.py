"""Access log middleware (Module 18)."""
from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware

from app.middleware.request_id import get_request_id

logger = logging.getLogger("http.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.monotonic()
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            status = 500
            duration_ms = (time.monotonic() - start) * 1000
            logger.exception(
                "%s %s -> EXCEPTION in %.1fms",
                request.method,
                request.url.path,
                duration_ms,
            )
            raise

        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "%s %s -> %d in %.1fms",
            request.method,
            request.url.path,
            status,
            duration_ms,
            extra={
                "request_id": get_request_id(),
                "method": request.method,
                "path": request.url.path,
                "status": status,
                "duration_ms": round(duration_ms, 1),
            },
        )
        return response
