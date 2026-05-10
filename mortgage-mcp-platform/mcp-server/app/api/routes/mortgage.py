"""Mortgage calculation HTTP API."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from app.metrics import MORTGAGE_CALCS, REQUEST_COUNTER, REQUEST_LATENCY
from app.schemas.mortgage import MortgageCalculateRequest, MortgageCalculateResponse
from app.services.mortgage_service import MortgageService

router = APIRouter()


def get_mortgage_service() -> MortgageService:
    return MortgageService()


@router.post("/calculate", response_model=MortgageCalculateResponse)
async def calculate_mortgage(
    body: MortgageCalculateRequest,
    service: MortgageService = Depends(get_mortgage_service),
) -> MortgageCalculateResponse:
    start = time.perf_counter()
    try:
        result = service.calculate(body)
        MORTGAGE_CALCS.labels(loan_type=body.loan.loan_type).inc()
        REQUEST_COUNTER.labels(method="POST", path="/mortgage/calculate", status="200").inc()
        return result
    finally:
        REQUEST_LATENCY.labels(method="POST", path="/mortgage/calculate").observe(time.perf_counter() - start)
