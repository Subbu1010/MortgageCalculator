"""Aggregate API router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import health, metrics_route, mortgage, rag

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(metrics_route.router, tags=["metrics"])
api_router.include_router(mortgage.router, prefix="/mortgage", tags=["mortgage"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
