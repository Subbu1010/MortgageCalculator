"""Mortgage calculation request and response models."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class LoanTerms(BaseModel):
    """Core loan parameters."""

    principal: float = Field(..., gt=0, description="Loan amount in currency units")
    annual_interest_rate: float = Field(..., gt=0, le=100, description="Nominal annual rate in percent")
    term_months: int = Field(..., gt=0, le=600, description="Amortization term in months")
    loan_type: Literal["fixed", "arm"] = "fixed"


class EscrowInputs(BaseModel):
    """Escrow-related monthly components."""

    annual_property_tax: float = Field(default=0.0, ge=0)
    annual_homeowners_insurance: float = Field(default=0.0, ge=0)
    annual_pmi_rate_percent: float | None = Field(
        default=None,
        ge=0,
        le=5,
        description="If set, PMI computed as percent of principal annualized",
    )
    ltv_percent: float | None = Field(
        default=None,
        gt=0,
        le=125,
        description="Loan-to-value percent; PMI auto if > 80 when pmi rate provided",
    )


class ARMScenario(BaseModel):
    """Adjustable-rate mortgage scenario schedule."""

    fixed_period_months: int = Field(default=60, ge=0, le=120)
    margin_percent: float = Field(default=2.25, ge=0, le=15, description="Added to index after fixed period")
    first_adjustment_cap_percent: float = Field(default=2.0, ge=0, le=15)
    subsequent_adjustment_cap_percent: float = Field(default=2.0, ge=0, le=15)
    lifetime_cap_percent: float = Field(default=5.0, ge=0, le=20)
    index_annual_rates: list[float] = Field(
        default_factory=list,
        description="Forecast index rates (annual %) per adjustment after fixed period",
    )


class MortgageCalculateRequest(BaseModel):
    """Full mortgage calculation input."""

    loan: LoanTerms
    escrow: EscrowInputs | None = None
    arm: ARMScenario | None = None
    amortization_months: int | None = Field(
        default=None,
        ge=1,
        le=600,
        description="Optional: limit amortization rows returned",
    )

    @model_validator(mode="after")
    def validate_arm(self) -> MortgageCalculateRequest:
        if self.loan.loan_type == "arm" and self.arm is None:
            raise ValueError("arm details are required when loan_type is 'arm'")
        return self


class AmortizationRow(BaseModel):
    """Single month in amortization schedule."""

    month_index: int
    payment: float
    principal_component: float
    interest_component: float
    balance_remaining: float
    note_rate_annual_percent: float


class MortgageSummary(BaseModel):
    """High-level payment breakdown."""

    monthly_pi: float
    monthly_property_tax: float
    monthly_insurance: float
    monthly_pmi: float
    monthly_total_payment: float
    total_interest_over_term: float
    total_payments_over_term: float


class MortgageCalculateResponse(BaseModel):
    """Mortgage calculation output."""

    summary: MortgageSummary
    amortization: list[AmortizationRow]
    assumptions: dict[str, str | float | int]


def monthly_payment_fixed_monthly_rate(principal: float, monthly_rate: float, n_months: int) -> float:
    """Level payment for fixed rate amortization."""
    if monthly_rate <= 0:
        return principal / n_months
    factor = math.pow(1 + monthly_rate, n_months)
    return principal * (monthly_rate * factor) / (factor - 1)
