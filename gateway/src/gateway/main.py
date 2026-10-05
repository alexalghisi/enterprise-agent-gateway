from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from gateway.api.middleware import AuditMiddleware
from gateway.api.routes import router
from gateway.api.schemas import ErrorBody, ErrorResponse
from gateway.config import Settings
from gateway.container import Container
from gateway.domain.errors import GatewayError
from gateway.observability import configure_logging
from gateway.wiring import build_container


async def _gateway_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, GatewayError)
    body = ErrorResponse(error=ErrorBody(code=exc.code, message=exc.message))
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    resolved = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if container is not None:
            app.state.container = container
            yield
            return
        async with build_container(resolved) as built:
            app.state.container = built
            yield

    app = FastAPI(
        title="Enterprise Agent Gateway",
        version="0.1.0",
        summary="Tools that let conversational AI agents act on an insurance system of record.",
        lifespan=lifespan,
    )
    app.add_middleware(AuditMiddleware)
    app.add_exception_handler(GatewayError, _gateway_error_handler)
    app.include_router(router)

    @app.get("/healthz", tags=["ops"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


def run() -> None:
    import uvicorn

    configure_logging()
    uvicorn.run(create_app(), host="0.0.0.0", port=8080, log_config=None)
