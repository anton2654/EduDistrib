from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.core.config import settings
from app.infrastructure.db.base import Base
from app.infrastructure.db.engine import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        if settings.db_init_on_startup:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
    except Exception as error:
        if settings.db_startup_strict:
            raise
        logger.warning(
            "Database startup initialization failed. "
            "Application will continue in non-strict mode. Error: %s",
            error,
        )

    try:
        yield
    finally:
        await engine.dispose()