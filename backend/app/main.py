from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import router as auth_router
from app.db import get_session
from app.errors import AppError, app_error_handler, request_validation_error_handler
from app.files.router import router as public_files_router
from app.library.router import router as library_router
from app.observability import RequestObservabilityMiddleware, configure_logging
from app.public_read.router import router as public_read_router
from app.publishing.router import router as publishing_router
from app.writings.router import router as writings_router

EXPECTED_ALEMBIC_HEAD = "0001_initial"
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


async def readiness(session: AsyncSession) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise AppError("database_not_ready", "Banco indisponível.", 503) from error

    try:
        current = await session.scalar(text("SELECT version_num FROM alembic_version"))
    except SQLAlchemyError as error:
        raise AppError("migration_not_ready", "Banco aguardando migração.", 503) from error

    if current != EXPECTED_ALEMBIC_HEAD:
        raise AppError("migration_not_ready", "Banco aguardando migração.", 503)
    return {"status": "ready", "database": "ok", "migration": "head"}


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Entrelinhas API")
    app.add_middleware(RequestObservabilityMiddleware)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.include_router(auth_router)
    app.include_router(library_router)
    app.include_router(writings_router)
    app.include_router(publishing_router)
    app.include_router(public_files_router)
    app.include_router(public_read_router)

    @app.get("/api/health/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/health/ready")
    async def ready(session: SessionDependency) -> dict[str, str]:
        return await readiness(session)

    return app


app = create_app()
