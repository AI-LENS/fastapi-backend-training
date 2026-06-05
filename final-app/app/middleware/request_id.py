"""Generate or accept an X-Request-ID for every request (Modules 18 + 20)."""
from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware


request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = request.headers.get("x-request-id") or str(uuid4())
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            request_id_var.reset(token)


def get_request_id() -> str | None:
    return request_id_var.get()
