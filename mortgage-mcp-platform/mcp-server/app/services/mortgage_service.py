"""Mortgage calculation service with fixed and ARM support."""

from __future__ import annotations

import math

from app.schemas.mortgage import (
    AmortizationRow,
    ARMScenario,
    EscrowInputs,
    LoanTerms,
    MortgageCalculateRequest,
    MortgageCalculateResponse,
    MortgageSummary,
    monthly_payment_fixed_monthly_rate,
)


class MortgageService:
    """Domain logic for mortgage scenario analysis."""

    def calculate(self, payload: MortgageCalculateRequest) -> MortgageCalculateResponse:
        loan = payload.loan
        escrow = payload.escrow or EscrowInputs()
        n = loan.term_months
        annual = loan.annual_interest_rate
        monthly_rate = annual / 100.0 / 12.0

        if loan.loan_type == "fixed":
            pi = monthly_payment_fixed_monthly_rate(loan.principal, monthly_rate, n)
            schedule = self._schedule_fixed(loan.principal, monthly_rate, n, pi)
        else:
            arm = payload.arm
            if arm is None:
                raise ValueError("ARM scenario required")
            schedule, final_pi = self._schedule_arm(loan.principal, annual / 100.0, n, arm)
            pi = final_pi

        tax_m = escrow.annual_property_tax / 12.0 if escrow.annual_property_tax else 0.0
        ins_m = escrow.annual_homeowners_insurance / 12.0 if escrow.annual_homeowners_insurance else 0.0
        pmi_m = self._pmi_monthly(loan.principal, escrow)

        total_m = pi + tax_m + ins_m + pmi_m
        total_paid = sum(r.payment for r in schedule) + tax_m * len(schedule) + ins_m * len(schedule) + pmi_m * len(
            schedule
        )
        interest_total = sum(r.interest_component for r in schedule)

        max_rows = payload.amortization_months or len(schedule)
        amort_slice = schedule[:max_rows]

        summary = MortgageSummary(
            monthly_pi=round(pi, 4),
            monthly_property_tax=round(tax_m, 4),
            monthly_insurance=round(ins_m, 4),
            monthly_pmi=round(pmi_m, 4),
            monthly_total_payment=round(total_m, 4),
            total_interest_over_term=round(interest_total, 4),
            total_payments_over_term=round(total_paid, 4),
        )

        assumptions = {
            "loan_type": loan.loan_type,
            "principal": loan.principal,
            "annual_rate_percent_initial": annual,
            "term_months": n,
            "pi_formula": "standard_level_payment_amortization",
            "pmi_rule": "annual_rate_percent * principal / 12 when LTV>80 or explicit rate",
        }

        return MortgageCalculateResponse(
            summary=summary,
            amortization=amort_slice,
            assumptions=assumptions,
        )

    @staticmethod
    def _pmi_monthly(principal: float, escrow: EscrowInputs) -> float:
        if escrow.annual_pmi_rate_percent is None:
            return 0.0
        force = escrow.ltv_percent is not None and escrow.ltv_percent > 80.0
        if force or escrow.ltv_percent is None:
            return principal * (escrow.annual_pmi_rate_percent / 100.0) / 12.0
        if escrow.ltv_percent <= 80.0:
            return 0.0
        return principal * (escrow.annual_pmi_rate_percent / 100.0) / 12.0

    @staticmethod
    def _schedule_fixed(principal: float, monthly_rate: float, n_months: int, payment: float) -> list[AmortizationRow]:
        balance = principal
        rows: list[AmortizationRow] = []
        annual_note = monthly_rate * 12.0 * 100.0
        for m in range(1, n_months + 1):
            interest = balance * monthly_rate
            principal_part = payment - interest
            if principal_part > balance:
                principal_part = balance
            balance = max(0.0, balance - principal_part)
            rows.append(
                AmortizationRow(
                    month_index=m,
                    payment=round(min(payment, interest + principal_part), 4),
                    principal_component=round(principal_part, 4),
                    interest_component=round(interest, 4),
                    balance_remaining=round(balance, 4),
                    note_rate_annual_percent=round(annual_note, 6),
                )
            )
            if balance <= 1e-9:
                break
        return rows

    def _schedule_arm(
        self,
        principal: float,
        annual_rate_initial: float,
        n_months: int,
        arm: ARMScenario,
    ) -> tuple[list[AmortizationRow], float]:
        """Simplified ARM: fixed period, then annual adjustments with caps."""
        balance = principal
        rows: list[AmortizationRow] = []
        start_rate = annual_rate_initial
        lifetime_floor_rate = max(0.0, start_rate - arm.lifetime_cap_percent / 100.0)
        lifetime_ceiling_rate = start_rate + arm.lifetime_cap_percent / 100.0

        fixed_end = arm.fixed_period_months
        idx_pos = 0

        m = 0
        current_annual = start_rate
        payment = monthly_payment_fixed_monthly_rate(principal, start_rate / 12.0, n_months)

        while m < n_months and balance > 1e-9:
            m += 1
            if m > fixed_end and (m - fixed_end) % 12 == 1:
                if idx_pos < len(arm.index_annual_rates):
                    index_pct = arm.index_annual_rates[idx_pos]
                    idx_pos += 1
                else:
                    index_pct = current_annual * 100.0
                fully_indexed = index_pct / 100.0 + arm.margin_percent / 100.0
                candidate = fully_indexed
                candidate = min(candidate, current_annual + arm.subsequent_adjustment_cap_percent / 100.0)
                candidate = max(candidate, current_annual - arm.subsequent_adjustment_cap_percent / 100.0)
                if m == fixed_end + 1:
                    candidate = min(
                        candidate,
                        current_annual + arm.first_adjustment_cap_percent / 100.0,
                    )
                    candidate = max(
                        candidate,
                        current_annual - arm.first_adjustment_cap_percent / 100.0,
                    )
                candidate = max(lifetime_floor_rate, min(lifetime_ceiling_rate, candidate))
                current_annual = candidate
                monthly_rate = current_annual / 12.0
                remaining = n_months - m + 1
                payment = monthly_payment_fixed_monthly_rate(balance, monthly_rate, remaining)

            monthly_rate = current_annual / 12.0
            interest = balance * monthly_rate
            principal_part = payment - interest
            if principal_part > balance:
                principal_part = balance
            balance = max(0.0, balance - principal_part)
            rows.append(
                AmortizationRow(
                    month_index=m,
                    payment=round(min(payment, interest + principal_part), 4),
                    principal_component=round(principal_part, 4),
                    interest_component=round(interest, 4),
                    balance_remaining=round(balance, 4),
                    note_rate_annual_percent=round(current_annual * 100.0, 6),
                )
            )

        return rows, payment
