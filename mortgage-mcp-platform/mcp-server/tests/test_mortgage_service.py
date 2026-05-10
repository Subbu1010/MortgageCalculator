"""Unit tests for mortgage calculation service."""

from __future__ import annotations

import pytest

from app.schemas.mortgage import ARMScenario, EscrowInputs, LoanTerms, MortgageCalculateRequest
from app.services.mortgage_service import MortgageService


def test_fixed_rate_basic() -> None:
    req = MortgageCalculateRequest(
        loan=LoanTerms(
            principal=300_000,
            annual_interest_rate=6.0,
            term_months=360,
            loan_type="fixed",
        ),
        escrow=EscrowInputs(annual_property_tax=3600, annual_homeowners_insurance=1200),
    )
    out = MortgageService().calculate(req)
    assert out.summary.monthly_pi > 0
    assert out.summary.monthly_total_payment >= out.summary.monthly_pi
    assert len(out.amortization) == 360


def test_arm_requires_scenario() -> None:
    with pytest.raises(ValueError):
        MortgageCalculateRequest(
            loan=LoanTerms(
                principal=300_000,
                annual_interest_rate=5.5,
                term_months=360,
                loan_type="arm",
            )
        )


def test_arm_generates_schedule() -> None:
    req = MortgageCalculateRequest(
        loan=LoanTerms(
            principal=400_000,
            annual_interest_rate=5.25,
            term_months=360,
            loan_type="arm",
        ),
        arm=ARMScenario(
            fixed_period_months=60,
            index_annual_rates=[5.5, 6.0, 6.25],
        ),
    )
    out = MortgageService().calculate(req)
    assert len(out.amortization) == 360
    distinct_rates = {round(r.note_rate_annual_percent, 4) for r in out.amortization}
    assert len(distinct_rates) >= 2
