"""Application entry point: map search first, optional experiments behind a flag."""

import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import cache, flights, regions, utils
from app.config.settings import settings
from app.core.database import check_db_connection, init_db
from app.core.exceptions import (
    general_exception_handler,
    http_exception_handler,
    sqlalchemy_exception_handler,
    validation_exception_handler,
)
from app.core.logging import setup_logging

logging.basicConfig(level=settings.LOG_LEVEL)


async def require_admin(x_admin_key: str | None = Header(None)):
    if not settings.ADMIN_API_KEY:
        raise HTTPException(503, "관리자 API가 비활성화되어 있습니다.")
    if not x_admin_key or not secrets.compare_digest(
        x_admin_key, settings.ADMIN_API_KEY
    ):
        raise HTTPException(401, "관리자 인증이 필요합니다.")


@asynccontextmanager
async def lifespan(app):
    setup_logging()
    if settings.INIT_DB_ON_STARTUP:
        init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    description="출발공항과 여행 월을 선택해 조회한 날짜 중 일본 지역별 최저가를 비교합니다.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
for router in [regions.router, flights.router, utils.router]:
    app.include_router(router, prefix="/api/v1")
app.include_router(
    cache.router, prefix="/api/v1", dependencies=[Depends(require_admin)]
)
if settings.ENABLE_EXPERIMENTAL_FEATURES:
    from app.api.v1 import llm, prediction

    app.include_router(
        llm.router, prefix="/api/v1", dependencies=[Depends(require_admin)]
    )
    app.include_router(
        prediction.router,
        prefix="/api/v1/prediction",
        dependencies=[Depends(require_admin)],
    )

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


@app.get("/", include_in_schema=False)
@app.get("/api", include_in_schema=False)
async def root_redirect():
    return RedirectResponse("/docs")


@app.get("/api/v1", tags=["System"])
@app.get("/api/v1/status", tags=["System"])
async def api_status():
    return {
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "experimental_features": settings.ENABLE_EXPERIMENTAL_FEATURES,
        "map": "/api/v1/regions/lowest-prices",
        "documentation": "/docs",
    }


@app.get("/health", tags=["System"])
def health_check():
    database_ok = check_db_connection()
    provider = flights.get_amadeus_service().source
    return JSONResponse(
        status_code=200 if database_ok else 503,
        content={
            "status": (
                "healthy"
                if database_ok and provider == "amadeus"
                else "degraded" if database_ok else "unhealthy"
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_connected": database_ok,
            "flight_source": provider,
            "cache": "redis" if flights.get_cache_service().is_connected else "memory",
        },
    )
