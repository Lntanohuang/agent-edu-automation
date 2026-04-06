"""
请求级中间件：自动注入 trace_id、记录请求耗时。

任何模块均可通过 ``trace_id_var.get()`` 获取当前请求的 trace_id，
无需手动逐层传递。
"""

from __future__ import annotations

import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

# ── 全局 ContextVar ─────────────────────────────────────────
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="no-trace")

logger = get_logger("middleware")


class RequestTraceMiddleware(BaseHTTPMiddleware):
    """为每个请求注入 trace_id 并记录起止日志。"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        tid = request.headers.get("x-trace-id") or uuid.uuid4().hex[:16]
        trace_id_var.set(tid)

        bound = logger.bind(trace_id=tid)
        bound.info(
            "request_started",
            method=request.method,
            path=str(request.url.path),
        )

        t0 = time.perf_counter()
        response = await call_next(request)
        elapsed = round(time.perf_counter() - t0, 3)

        bound.info(
            "request_completed",
            status=response.status_code,
            elapsed_s=elapsed,
        )
        response.headers["X-Trace-Id"] = tid
        return response
