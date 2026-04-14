import logging

import asyncpg
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError

logger = logging.getLogger(__name__)

DB_UNAVAILABLE_DETAIL = (
    "Database is unavailable. Start PostgreSQL and verify DATABASE_URL settings."
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(IntegrityError)
    async def sqlalchemy_integrity_error_handler(
        request: Request,
        error: IntegrityError,
    ) -> JSONResponse:
        logger.warning(
            "Data integrity error on %s %s: %s",
            request.method,
            request.url.path,
            error,
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "Data conflict: check uniqueness and foreign key constraints."},
        )

    @app.exception_handler(OperationalError)
    async def sqlalchemy_operational_error_handler(
        request: Request,
        error: OperationalError,
    ) -> JSONResponse:
        logger.error(
            "Operational database error on %s %s: %s",
            request.method,
            request.url.path,
            error,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": DB_UNAVAILABLE_DETAIL},
        )

    @app.exception_handler(asyncpg.PostgresConnectionError)
    async def asyncpg_connection_error_handler(
        request: Request,
        error: asyncpg.PostgresConnectionError,
    ) -> JSONResponse:
        logger.error(
            "PostgreSQL connection error on %s %s: %s",
            request.method,
            request.url.path,
            error,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": DB_UNAVAILABLE_DETAIL},
        )
