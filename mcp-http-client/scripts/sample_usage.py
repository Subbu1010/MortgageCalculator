#!/usr/bin/env python3
"""Example asyncio usage of MortgageClient."""

from __future__ import annotations

import asyncio
import json
import os

from mcp_client.client import MortgageClient


async def demo() -> None:
    os.environ.setdefault("MCP_SERVER_BASE_URL", "http://localhost:8000")
    client = MortgageClient.from_env()

    print("--- health ---")
    print(await client.health())

    print("--- mortgage (fixed) ---")
    payload = {
        "loan": {
            "principal": 420_000,
            "annual_interest_rate": 6.375,
            "term_months": 360,
            "loan_type": "fixed",
        },
        "escrow": {
            "annual_property_tax": 4800,
            "annual_homeowners_insurance": 1800,
            "annual_pmi_rate_percent": 0.55,
            "ltv_percent": 87,
        },
        "amortization_months": 6,
    }
    calc = await client.mortgage_calculate(payload)
    print(json.dumps(calc["summary"], indent=2))

    print("--- rag (requires GOOGLE_API_KEY on server) ---")
    try:
        rag = await client.rag_query("What are debt-to-income limits for agency loans?", top_k=3)
        print(json.dumps({k: rag[k] for k in ("answer", "model_used")}, indent=2))
        print(f"sources count: {len(rag.get('sources', []))}")
    except Exception as exc:  # noqa: BLE001
        print(f"RAG skipped or failed: {exc}")


if __name__ == "__main__":
    asyncio.run(demo())
