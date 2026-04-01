from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import APP_TITLE
from .logging_config import configure_logging
from .routers import admin_router, ingest_router, query_router, system_router
from .services.lifecycle import on_shutdown, on_startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    await on_startup(app)
    try:
        yield
    finally:
        await on_shutdown(app)


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title=APP_TITLE, lifespan=lifespan)
    app.include_router(system_router)
    app.include_router(ingest_router)
    app.include_router(query_router)
    app.include_router(admin_router)
    return app


app = create_app()
