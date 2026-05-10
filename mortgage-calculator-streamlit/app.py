"""
Standalone Streamlit mortgage calculator UI.

Calls the MCP HTTP API POST /mortgage/calculate (FastAPI server).
Mirrors all request fields: LoanTerms, EscrowInputs (optional), ARMScenario (optional),
and amortization_months (optional).
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
import pandas as pd
import streamlit as st


def parse_float_list(text: str) -> list[float]:
    out: list[float] = []
    for part in text.replace("\n", ",").split(","):
        part = part.strip()
        if not part:
            continue
        out.append(float(part))
    return out


def build_mortgage_payload(
    *,
    principal: float,
    annual_interest_rate: float,
    term_months: int,
    loan_type: str,
    include_escrow: bool,
    annual_property_tax: float,
    annual_homeowners_insurance: float,
    include_pmi_rate: bool,
    annual_pmi_rate_percent: float,
    include_ltv: bool,
    ltv_percent: float,
    limit_amortization_rows: bool,
    amortization_months: int,
    include_arm_block: bool,
    arm_fixed_period_months: int,
    arm_margin_percent: float,
    arm_first_adjustment_cap_percent: float,
    arm_subsequent_adjustment_cap_percent: float,
    arm_lifetime_cap_percent: float,
    arm_index_annual_rates: list[float],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "loan": {
            "principal": principal,
            "annual_interest_rate": annual_interest_rate,
            "term_months": term_months,
            "loan_type": loan_type,
        },
    }

    if include_escrow:
        escrow: dict[str, Any] = {
            "annual_property_tax": annual_property_tax,
            "annual_homeowners_insurance": annual_homeowners_insurance,
        }
        if include_pmi_rate:
            escrow["annual_pmi_rate_percent"] = annual_pmi_rate_percent
        if include_ltv:
            escrow["ltv_percent"] = ltv_percent
        payload["escrow"] = escrow

    if limit_amortization_rows:
        payload["amortization_months"] = amortization_months

    if loan_type == "arm" and include_arm_block:
        payload["arm"] = {
            "fixed_period_months": arm_fixed_period_months,
            "margin_percent": arm_margin_percent,
            "first_adjustment_cap_percent": arm_first_adjustment_cap_percent,
            "subsequent_adjustment_cap_percent": arm_subsequent_adjustment_cap_percent,
            "lifetime_cap_percent": arm_lifetime_cap_percent,
            "index_annual_rates": arm_index_annual_rates,
        }

    return payload


def main() -> None:
    st.set_page_config(page_title="Mortgage Calculator", layout="wide")
    st.title("Mortgage calculator")
    st.caption(
        "Standalone UI — full `MortgageCalculateRequest` payload for `POST /mortgage/calculate`. "
        "Start the MCP FastAPI server separately."
    )

    with st.sidebar:
        base_url = st.text_input(
            "API base URL",
            value=os.environ.get("MCP_SERVER_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
            help="FastAPI root (no trailing slash).",
        )
        timeout = st.slider("Request timeout (seconds)", 5, 120, 30)

        st.divider()
        if st.button("Check API health"):
            try:
                r = httpx.get(f"{base_url}/health", timeout=timeout)
                r.raise_for_status()
                st.success(r.json())
            except Exception as exc:
                st.error(str(exc))

    tabs = st.tabs(["Loan", "Escrow", "ARM scenario", "Schedule options"])

    with tabs[0]:
        st.markdown("#### `loan` — LoanTerms")
        lc1, lc2 = st.columns(2)
        with lc1:
            principal = st.number_input(
                "`principal` — loan amount",
                min_value=1.0,
                max_value=500_000_000.0,
                value=350_000.0,
                step=1_000.0,
                help="Currency units; must be > 0.",
            )
            annual_interest_rate = st.number_input(
                "`annual_interest_rate` — nominal annual %",
                min_value=0.01,
                max_value=100.0,
                value=6.25,
                step=0.001,
                format="%.4f",
                help="Percent (e.g. 6.25 for 6.25%). API: > 0 and ≤ 100.",
            )
        with lc2:
            term_months = st.number_input(
                "`term_months`",
                min_value=1,
                max_value=600,
                value=360,
                step=1,
                help="Amortization term in months (API: 1–600).",
            )
            loan_type = st.selectbox(
                "`loan_type`",
                options=["fixed", "arm"],
                index=0,
                help="If `arm`, the API requires an `arm` object.",
            )

    with tabs[1]:
        st.markdown("#### `escrow` — EscrowInputs (optional)")
        include_escrow = st.checkbox(
            "Include `escrow` object in JSON",
            value=True,
            help="If off, `escrow` key is omitted (same as null optional escrow).",
        )
        ec1, ec2 = st.columns(2)
        with ec1:
            annual_property_tax = st.number_input(
                "`annual_property_tax`",
                min_value=0.0,
                value=4_200.0,
                step=50.0,
                disabled=not include_escrow,
                help="≥ 0",
            )
            include_pmi_rate = st.checkbox(
                "Include `annual_pmi_rate_percent`",
                value=False,
                disabled=not include_escrow,
                help="When checked, key is sent (PMI as %% of principal per year). Omit key when unchecked.",
            )
            annual_pmi_rate_percent = st.number_input(
                "`annual_pmi_rate_percent`",
                min_value=0.0,
                max_value=5.0,
                value=0.45,
                step=0.01,
                format="%.3f",
                disabled=not include_escrow or not include_pmi_rate,
                help="0–5 when present.",
            )
        with ec2:
            annual_homeowners_insurance = st.number_input(
                "`annual_homeowners_insurance`",
                min_value=0.0,
                value=1_500.0,
                step=25.0,
                disabled=not include_escrow,
                help="≥ 0",
            )
            include_ltv = st.checkbox(
                "Include `ltv_percent`",
                value=False,
                disabled=not include_escrow,
                help="When checked, key is sent (LTV drives PMI behavior when PMI rate is set).",
            )
            ltv_percent = st.number_input(
                "`ltv_percent`",
                min_value=1.0,
                max_value=125.0,
                value=88.0,
                step=0.1,
                disabled=not include_escrow or not include_ltv,
                help="> 0 and ≤ 125 when present.",
            )

    with tabs[2]:
        st.markdown("#### `arm` — ARMScenario (required when `loan_type` is `arm`)")
        include_arm_block = st.checkbox(
            "Include `arm` object when loan type is ARM",
            value=True,
            disabled=(loan_type != "arm"),
            help="Uncheck to simulate an invalid request (ARM without arm block). Normally leave on for ARM.",
        )
        if loan_type != "arm":
            st.info("Switch **loan_type** to **arm** to edit ARM fields. Payload omits `arm` for fixed-rate loans.")

        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            arm_fixed_period_months = st.number_input(
                "`fixed_period_months`",
                min_value=0,
                max_value=120,
                value=60,
                disabled=loan_type != "arm",
                help="0–120",
            )
            arm_margin_percent = st.number_input(
                "`margin_percent` — added to index after fixed period",
                min_value=0.0,
                max_value=15.0,
                value=2.25,
                step=0.05,
                disabled=loan_type != "arm",
                help="0–15",
            )
            arm_first_adjustment_cap_percent = st.number_input(
                "`first_adjustment_cap_percent`",
                min_value=0.0,
                max_value=15.0,
                value=2.0,
                step=0.05,
                disabled=loan_type != "arm",
                help="0–15",
            )
        with ac2:
            arm_subsequent_adjustment_cap_percent = st.number_input(
                "`subsequent_adjustment_cap_percent`",
                min_value=0.0,
                max_value=15.0,
                value=2.0,
                step=0.05,
                disabled=loan_type != "arm",
                help="0–15",
            )
            arm_lifetime_cap_percent = st.number_input(
                "`lifetime_cap_percent`",
                min_value=0.0,
                max_value=20.0,
                value=5.0,
                step=0.05,
                disabled=loan_type != "arm",
                help="0–20",
            )
        arm_index_raw = st.text_area(
            "`index_annual_rates` — forecast index (annual %%), comma or newline separated",
            value="5.5, 6.0, 6.25",
            disabled=loan_type != "arm",
            help="One rate per yearly adjustment after the fixed period; may be empty [].",
        )

    with tabs[3]:
        st.markdown("#### `amortization_months` — optional response trim")
        limit_amortization_rows = st.checkbox(
            "Send `amortization_months`",
            value=True,
            help="If off, key is omitted (API returns full schedule length).",
        )
        amortization_months = st.number_input(
            "`amortization_months` — max rows in response",
            min_value=1,
            max_value=600,
            value=24,
            disabled=not limit_amortization_rows,
            help="1–600 when present.",
        )

    arm_index_annual_rates = parse_float_list(arm_index_raw) if loan_type == "arm" else []

    payload = build_mortgage_payload(
        principal=principal,
        annual_interest_rate=annual_interest_rate,
        term_months=int(term_months),
        loan_type=loan_type,
        include_escrow=include_escrow,
        annual_property_tax=annual_property_tax,
        annual_homeowners_insurance=annual_homeowners_insurance,
        include_pmi_rate=include_pmi_rate,
        annual_pmi_rate_percent=annual_pmi_rate_percent,
        include_ltv=include_ltv,
        ltv_percent=ltv_percent,
        limit_amortization_rows=limit_amortization_rows,
        amortization_months=int(amortization_months),
        include_arm_block=include_arm_block if loan_type == "arm" else False,
        arm_fixed_period_months=int(arm_fixed_period_months),
        arm_margin_percent=float(arm_margin_percent),
        arm_first_adjustment_cap_percent=float(arm_first_adjustment_cap_percent),
        arm_subsequent_adjustment_cap_percent=float(arm_subsequent_adjustment_cap_percent),
        arm_lifetime_cap_percent=float(arm_lifetime_cap_percent),
        arm_index_annual_rates=arm_index_annual_rates,
    )

    with st.expander("Preview outgoing JSON body", expanded=False):
        st.code(json.dumps(payload, indent=2), language="json")

    col_go, col_warn = st.columns([1, 3])
    with col_go:
        calculate = st.button("Calculate", type="primary")
    with col_warn:
        if loan_type == "arm" and not include_arm_block:
            st.warning("API validation error expected: ARM loans require an `arm` object.")

    if calculate:
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(f"{base_url}/mortgage/calculate", json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            st.error(f"HTTP {exc.response.status_code}: {exc.response.text}")
            return
        except Exception as exc:
            st.error(f"Request failed: {exc}")
            return

        summary = data.get("summary", {})
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Monthly P&I", f"${summary.get('monthly_pi', 0):,.2f}")
        m2.metric("Monthly total", f"${summary.get('monthly_total_payment', 0):,.2f}")
        m3.metric("Total interest (term)", f"${summary.get('total_interest_over_term', 0):,.2f}")
        m4.metric("Total payments (term)", f"${summary.get('total_payments_over_term', 0):,.2f}")

        st.subheader("Monthly breakdown")
        b1, b2, b3 = st.columns(3)
        b1.metric("Property tax / mo", f"${summary.get('monthly_property_tax', 0):,.2f}")
        b2.metric("Insurance / mo", f"${summary.get('monthly_insurance', 0):,.2f}")
        b3.metric("PMI / mo", f"${summary.get('monthly_pmi', 0):,.2f}")

        if data.get("assumptions"):
            with st.expander("Assumptions"):
                st.json(data["assumptions"])

        rows = data.get("amortization") or []
        if rows:
            df = pd.DataFrame(rows)
            st.subheader("Amortization schedule")
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "payment": st.column_config.NumberColumn("Payment", format="$%.2f"),
                    "principal_component": st.column_config.NumberColumn("Principal", format="$%.2f"),
                    "interest_component": st.column_config.NumberColumn("Interest", format="$%.2f"),
                    "balance_remaining": st.column_config.NumberColumn("Balance", format="$%.2f"),
                    "note_rate_annual_percent": st.column_config.NumberColumn("Note rate %", format="%.4f"),
                    "month_index": st.column_config.NumberColumn("Month", format="%d"),
                },
            )


if __name__ == "__main__":
    main()
