# MCP HTTP client

Standalone Python project: **`httpx`** async client and **CLI** for the mortgage MCP REST API (`/health`, `/mortgage/calculate`, `/rag/query`).  
This code used to live under `mortgage-mcp-platform/mcp-client`; it now sits beside that repo.

## Setup (Windows)

```powershell
cd d:\Study\MortgageCalculator\mcp-http-client
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

## Environment

Copy `.env.example` or set:

- `MCP_SERVER_BASE_URL` — default `http://localhost:8000`
- `REQUEST_TIMEOUT_SECONDS` — default `120`

## CLI

```powershell
$env:MCP_SERVER_BASE_URL = "http://127.0.0.1:8000"
.\.venv\Scripts\python.exe -m mcp_client.cli health
.\.venv\Scripts\python.exe -m mcp_client.cli calc "{\"loan\":{\"principal\":300000,\"annual_interest_rate\":6,\"term_months\":360,\"loan_type\":\"fixed\"}}"
.\.venv\Scripts\python.exe -m mcp_client.cli rag "Summarize escrow policy" --top-k 3
```

## Docker / Compose

From **`mortgage-mcp-platform`**, Compose builds this client with `context: ../mcp-http-client` (profile `client`).

## Helm

Chart path: `helm/mcp-client/` inside this project.

```bash
helm upgrade --install mcp-client ./helm/mcp-client -n your-namespace
```

## Tests

```powershell
.\.venv\Scripts\pytest -q
```
