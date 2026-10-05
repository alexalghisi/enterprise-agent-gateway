from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

audit_log = logging.getLogger("gateway.audit")

REQUEST_ID_HEADER = "X-Request-Id"


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        started = time.perf_counter()
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        principal = getattr(request.state, "principal", None)
        route = request.scope.get("route")
        audit_log.info(
            "tool_call",
            extra={
                "fields": {
                    "request_id": request_id,
                    "tenant_id": principal.tenant_id if principal else None,
                    "agent_id": principal.agent_id if principal else None,
                    "method": request.method,
                    "route": getattr(route, "path", request.url.path),
                    "status": response.status_code,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                }
            },
        )
        return response
