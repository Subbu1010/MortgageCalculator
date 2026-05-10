# Mortgage MCP Platform

Enterprise-ready **FastAPI** service for mortgage amortization modeling and **RAG** retrieval over internal policy documents stored in **PostgreSQL + pgvector**, with optional **Model Context Protocol (MCP)** stdio tools for AI clients.

## Architecture (ASCII)

```
┌──────────────────┐     HTTP/SSE       ┌─────────────────────────────┐
│ MCP HTTP Client  │ ────────────────► │ FastAPI (mcp-server)        │
│ (mcp-http-client)│   /mortgage/*     │  • MortgageService          │
└────────┬─────────┘   /rag/*         │  • RAGService + LangChain   │
         │                             │  • Repositories (SQLAlchemy)│
         │ MCP stdio (optional proc)    └──────────────┬──────────────┘
         │                                             │
         └──────────────►┌──────────────────┐   asyncPg / Alembic
                          │ MCP stdio_server │ ──────────┐
                          └──────────────────┘           ▼
                                            ┌────────────────────────┐
                                            │ PostgreSQL + pgvector  │
                                            │ documents / chunks /     │
                                            │ embeddings / audit_logs  │
                                            └────────────────────────┘
```

Ingress path: ingestion scans `/data/documents` (txt, md, pdf), splits with configurable overlap, calls **Google Generative AI embeddings**, writes vectors (`cosine` ordering via `<=>`), and persists audit rows.

## Repository layout

| Path | Purpose |
|------|---------|
| `mcp-server/` | FastAPI app, MCP stdio, Alembic, Dockerfile |
| `../mcp-http-client/` (sibling folder) | `httpx` async client + CLI; Helm chart at `mcp-http-client/helm/mcp-client/` |
| `sample-documents/` | 18+ curated policy/procedure/regulatory texts |
| `database/init/` | `CREATE EXTENSION vector` bootstrap for Postgres image |
| `helm/mcp-server` | Server Helm chart (client chart ships with `mcp-http-client`) |
| `openshift/raw/` | Illustrative manifests for `oc apply` |
| `scripts/` | `curl-examples.sh`, PDF generator |
| `docs/openshift-deployment.md` | Build, secrets, Helm, SCC notes |

## Prerequisites

- **Python 3.12** (container base image); local 3.10+ may work with current dependencies.
- **PostgreSQL 16** with **pgvector** (`pgvector/pgvector:pg16` in Compose).
- **Google AI Studio API key** for embeddings (`models/text-embedding-004`) and Gemini answers (`GEMINI_MODEL`, default `gemini-1.5-flash`).

Without `GOOGLE_API_KEY`, the API still calculates mortgages; ingestion short-circuits and RAG returns a configuration warning.

### Local PostgreSQL (defaults)

Compose maps `localhost:5432` with:

- user / password / database: `postgres` / `postgres` / `mortgage`

## Quick start — Docker Compose

```bash
cd mortgage-mcp-platform
cp .env.example .env   # add GOOGLE_API_KEY for embeddings + LLM answers
docker compose up --build
```

Endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness/readiness probe |
| `GET` | `/metrics` | Prometheus text exposition |
| `POST` | `/mortgage/calculate` | Amortization, escrow, PMI, ARM scenarios |
| `POST` | `/rag/query` | Retrieve chunks + Gemini-grounded narrative |

Automatic startup (`startup.sh`): wait for Postgres → Alembic `upgrade head` → ingest `/data/documents` (Compose bind-mounts `./sample-documents`).

## Configure chunking / vectors

Environment variables (`mcp-server/.env.example`):

| Variable | Default | Notes |
|---------|---------|-------|
| `CHUNK_SIZE` | `1200` | LangChain splitter |
| `CHUNK_OVERLAP` | `200` | Sliding window |
| `EMBEDDING_DIMENSIONS` | `768` | Must match Alembic `Vector(768)` |
| `RAG_SIMILARITY_THRESHOLD` | `0.65` | Ceiling on pgvector cosine **distance** (lower stricter) |
| `RAG_TOP_K` | `5` | Retrieved chunks |

If you change embedding dimensions, add a new Alembic revision altering the `embeddings.embedding` column.

## HTTP examples (curl)

```bash
export BASE=http://localhost:8000

curl -sS "$BASE/health"

curl -sS -X POST "$BASE/mortgage/calculate" \
  -H 'Content-Type: application/json' \
  -d '{
    "loan": {
      "principal": 400000,
      "annual_interest_rate": 6.25,
      "term_months": 360,
      "loan_type": "arm"
    },
    "arm": {
      "fixed_period_months": 60,
      "margin_percent": 2.25,
      "index_annual_rates": [5.6, 6.1, 6.4]
    },
    "escrow": {
      "annual_property_tax": 6000,
      "annual_homeowners_insurance": 1800
    },
    "amortization_months": 12
  }'

curl -sS -X POST "$BASE/rag/query" \
  -H 'Content-Type: application/json' \
  -d '{"query":"What are FHA case binder requirements?","top_k":4}'
```

More samples: `scripts/curl-examples.sh`.

## MCP stdio server (tools)

Run inside the same environment as the HTTP image (DB reachable, `PYTHONPATH=/app`):

```bash
cd mcp-server
export DATABASE_HOST=localhost
python -m app.mcp.stdio_server
```

### Example `mortgage_calculate` tool call (JSON params)

Request (abbreviated):

```json
{
  "name": "mortgage_calculate",
  "arguments": {
    "payload": {
      "loan": {
        "principal": 350000,
        "annual_interest_rate": 5.875,
        "term_months": 300,
        "loan_type": "fixed"
      },
      "escrow": {
        "annual_property_tax": 3200,
        "annual_homeowners_insurance": 1100
      }
    }
  }
}
```

Response content (text JSON excerpt):

```json
{
  "summary": {
    "monthly_pi": 2483.12,
    "monthly_property_tax": 266.67,
    "monthly_insurance": 91.67,
    "monthly_pmi": 0.0,
    "monthly_total_payment": 2841.46
  }
}
```

### Example `rag_query` tool call

```json
{
  "name": "rag_query",
  "arguments": {
    "query": "Outline fair lending documentation expectations",
    "top_k": 3
  }
}
```

## MCP HTTP client

The HTTP client lives in the separate project **`mcp-http-client/`** next to this folder. Docker Compose (`profile: client`) builds it from `../mcp-http-client`.

```bash
cd ../mcp-http-client
pip install -r requirements.txt
export MCP_SERVER_BASE_URL=http://localhost:8000
python -m mcp_client.cli health
python -m mcp_client.cli rag "Summarize AML triggers" --top-k 5 --stream
python scripts/sample_usage.py
```

See `mcp-http-client/README.md` for details.

## Helm (OpenShift / Kubernetes)

```bash
helm upgrade --install mortgage-mcp helm/mcp-server \
  --set image.repository=quay.io/your-org/mcp-server \
  --set database.host=postgresql.platform.svc \
  --set database.password="$DBPW" \
  --set secrets.googleApiKey="$GOOGLE_API_KEY" \
  --set route.host=mortgage-mcp.apps.cluster.example.com
```

Charts include `Deployment`, `Service`, `Route` (toggle), `ConfigMap`, `Secret`, `ServiceAccount`, and optional `HorizontalPodAutoscaler`.

Mount policy documents via `extraVolumes` / `extraVolumeMounts` in `helm/mcp-server/values.yaml` or bake them into a custom container image layer.

Detailed OpenShift workflows: [`docs/openshift-deployment.md`](docs/openshift-deployment.md).

## Makefile & tests

Unix-like environments:

```bash
make install     # creates .venv locally
make test        # pytest in mcp-server
```

Pytest exemplars validate fixed and ARM calculators (`mcp-server/tests/test_mortgage_service.py`).

## Security checklist

- Secrets only via Kubernetes `Secret`/OpenShift `Secret`, never baked into images.
- SQLAlchemy ORM exclusively (parameterized queries) for SQL injection defense.
- Pydantic request models enforce bounds on loan economics and query length.
- Audit rows written for ingestion lifecycle and each RAG query.
- Containers run non-root (`1001` server, `1002` client) with dropped capabilities.

## Troubleshooting

| Symptom | Mitigation |
|---------|------------|
| Startup waits then fails DB | Confirm host/port/users match; check `DATABASE_*` vars. Compose service name `postgres`. |
| Ingest logged `missing GOOGLE_API_KEY` | Export key in Compose `.env`. |
| Embedding dimension errors | Align `EMBEDDING_DIMENSIONS` with model output and Alembic vector column. |
| Empty RAG answers | Ensure ingestion ran; lower `RAG_SIMILARITY_THRESHOLD`; verify chunks exist in DB. |
| MCP import errors | Pin `mcp` per `requirements.txt`; API drift—match `on_list_tools`/`on_call_tool` signatures. |

## Scaling guidance

- Horizontally scale stateless `mcp-server` pods; keep **one writer** for heavy re-ingestion jobs or run ingest as a `Job`.
- Tune Postgres `max_connections` vs. SQLAlchemy pool (`DATABASE_POOL_SIZE`).
- Add pgvector ANN index (IVFFlat/HNSW) after sufficient row counts; re-run `ANALYZE embeddings`.

## Regenerating the sample PDF

```bash
pip install reportlab pypdf
python scripts/make_sample_pdf.py
```

---

**Disclaimer:** Sample policies are synthetic training material only—not legal, regulatory, or underwriting advice.
