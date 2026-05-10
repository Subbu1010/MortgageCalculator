# Mortgage calculator — Streamlit UI

Standalone web UI that talks to the **MCP mortgage HTTP API** (`POST /mortgage/calculate`).  
This folder is **not** part of `mcp-server` or `mcp-client`; install and run it on its own.

## Prerequisites

- Python 3.10+
- Mortgage API running (e.g. `uvicorn` on `http://127.0.0.1:8000`)

## Setup

```powershell
cd mortgage-calculator-streamlit
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

Optional: copy `.env.example` and set `MCP_SERVER_BASE_URL`, or enter the URL in the sidebar.

## Run

```powershell
.\.venv\Scripts\streamlit run app.py
```

Browser opens at `http://localhost:8501` by default.

The UI exposes every **`MortgageCalculateRequest`** field: `loan` (all `LoanTerms`), optional `escrow` (`EscrowInputs` with optional PMI/LTV keys), optional `arm` (`ARMScenario`, including `index_annual_rates`), and optional `amortization_months`. Use **Preview outgoing JSON** to verify the body before **Calculate**.

## Troubleshooting

- Use **Check API health** in the sidebar if calculations fail.
- The UI calls the API from Python (`httpx`); ensure the base URL is reachable from the machine where Streamlit runs.
