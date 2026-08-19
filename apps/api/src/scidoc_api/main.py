from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scidoc_core.config import Settings, get_settings
from scidoc_database.session import configure_database, create_schema
from scidoc_observability.logging import configure_logging

from scidoc_api.middleware.request_id import RequestIdMiddleware
from scidoc_api.routes import (
    capabilities,
    documents,
    elements,
    exports,
    jobs,
    narration,
    pages,
    search,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    configure_logging(
        runtime_settings.log_level, json_output=runtime_settings.environment != "local"
    )
    configure_database(runtime_settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        runtime_settings.storage_root.mkdir(parents=True, exist_ok=True)
        create_schema()
        yield

    application = FastAPI(
        title="Scientific Document Intelligence API",
        version="0.1.0",
        description="Local-first PDF-to-SDR processing API",
        lifespan=lifespan,
    )
    application.state.settings = runtime_settings
    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=runtime_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )
    for router in (
        capabilities.router,
        documents.router,
        pages.router,
        elements.router,
        jobs.router,
        search.router,
        exports.router,
        narration.router,
    ):
        application.include_router(router)

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    @application.get("/")
    def root() -> dict[str, str]:
        return {"name": "Scientific Document Intelligence API", "docs": "/docs"}

    return application


app = create_app()
