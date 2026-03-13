import time
import uuid
import structlog
from fastapi import FastAPI, Request, Response
from app.core.exceptions import AppException, app_exception_handler, unhandled_exception_handler

logger = structlog.get_logger()


def register_middlewares(app: FastAPI) -> None:
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    @app.middleware("http")
    async def trace_middleware(request: Request, call_next) -> Response:
        trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4())[:8])
        correlation_id = request.headers.get("X-Correlation-Id", str(uuid.uuid4())[:8])

        request.state.trace_id = trace_id
        request.state.correlation_id = correlation_id

        start = time.perf_counter()

        logger.info(
            "request_started",
            trace_id=trace_id,
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
        )

        response: Response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "request_finished",
            trace_id=trace_id,
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Correlation-Id"] = correlation_id

        return response
