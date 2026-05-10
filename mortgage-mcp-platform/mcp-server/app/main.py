"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import get_settings
from app.core.exceptions import AppError
from app.core.logging_config import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.db.session import dispose_engine, init_engine

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_engine(settings)
    yield
    await dispose_engine()


app = FastAPI(
    title="Mortgage MCP Server",
    version="1.0.0",
    description="Enterprise mortgage calculations and RAG over internal banking policy documents.",
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)
app.include_router(api_router)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": exc.code, "message": str(exc)})


@app.exception_handler(RequestValidationError)
async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": "validation_error", "detail": exc.errors()})
