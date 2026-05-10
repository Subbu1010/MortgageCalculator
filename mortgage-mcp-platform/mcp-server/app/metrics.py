"""Prometheus metrics definitions."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

REQUEST_COUNTER = Counter(
    "mortgage_http_requests_total",
    "Total HTTP requests processed by the MCP mortgage server",
    labelnames=("method", "path", "status"),
)

REQUEST_LATENCY = Histogram(
    "mortgage_http_request_latency_seconds",
    "Latency of HTTP requests in seconds",
    labelnames=("method", "path"),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, float("inf")),
)

MORTGAGE_CALCS = Counter(
    "mortgage_calculations_total",
    "Mortgage calculations completed",
    labelnames=("loan_type",),
)

RAG_QUERIES = Counter(
    "mortgage_rag_queries_total",
    "RAG queries served",
    labelnames=("status",),
)
