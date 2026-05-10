#!/usr/bin/env sh
set -e
BASE="${MCP_SERVER_BASE_URL:-http://localhost:8000}"

echo "== Health =="
curl -sS "${BASE}/health" | jq .

echo "== Metrics (first lines) =="
curl -sS "${BASE}/metrics" | head -n 5

echo "== Mortgage fixed =="
curl -sS -X POST "${BASE}/mortgage/calculate" \
  -H 'Content-Type: application/json' \
  -d '{
    "loan": {
      "principal": 350000,
      "annual_interest_rate": 6.125,
      "term_months": 360,
      "loan_type": "fixed"
    },
    "escrow": {
      "annual_property_tax": 4200,
      "annual_homeowners_insurance": 1500,
      "annual_pmi_rate_percent": 0.45,
      "ltv_percent": 88
    },
    "amortization_months": 3
  }' | jq '.summary'

echo "== RAG (requires GOOGLE_API_KEY on server) =="
curl -sS -X POST "${BASE}/rag/query" \
  -H 'Content-Type: application/json' \
  -d '{"query":"Summarize escrow surplus handling policy","top_k":3}' | jq '{model_used, answer: .answer[0:400], sources: (.sources|length)}'
