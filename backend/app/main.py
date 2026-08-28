from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import AppError, app_error_handler

EXPECTED_ALEMBIC_HEAD = "0001_initial"
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


async def readiness(session: AsyncSession) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    current = await session.scalar(text("SELECT version_num FROM alembic_version"))
    if current != EXPECTED_ALEMBIC_HEAD:
        raise AppError("migration_not_ready", "Banco aguardando migração.", 503)
    return {"status": "ready", "database": "ok", "migration": "head"}


def create_app() -> FastAPI:
    app = FastAPI(title="Entrelinhas API")
    app.add_exception_handler(AppError, app_error_handler)

    @app.get("/api/health/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/health/ready")
    async def ready(session: SessionDependency) -> dict[str, str]:
        return await readiness(session)

    return app


app = create_app()
