"""RAG query HTTP API."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.dependencies import DbSession, SettingsDep
from app.metrics import RAG_QUERIES, REQUEST_COUNTER, REQUEST_LATENCY
from app.repositories.audit_repository import AuditRepository
from app.repositories.embedding_repository import EmbeddingRepository
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse
from app.services.rag_service import RAGService

router = APIRouter()


@router.post("/query", response_model=None)
async def rag_query(
    body: RAGQueryRequest,
    session: DbSession,
    settings: SettingsDep,
):
    svc = RAGService(
        settings=settings,
        embeddings=EmbeddingRepository(session),
        audit=AuditRepository(session),
    )
    start = time.perf_counter()
    if body.stream:

        async def event_stream() -> AsyncIterator[bytes]:
            result = await svc.query(RAGQueryRequest(query=body.query, top_k=body.top_k, stream=False))
            payload = json.dumps(result.model_dump())
            yield f"data: {payload}\n\n".encode("utf-8")

        RAG_QUERIES.labels(status="stream").inc()
        REQUEST_COUNTER.labels(method="POST", path="/rag/query", status="200").inc()
        REQUEST_LATENCY.labels(method="POST", path="/rag/query").observe(time.perf_counter() - start)
        return StreamingResponse(event_stream(), media_type="text/event-stream")

    result: RAGQueryResponse = await svc.query(body)
    RAG_QUERIES.labels(status="ok").inc()
    REQUEST_COUNTER.labels(method="POST", path="/rag/query", status="200").inc()
    REQUEST_LATENCY.labels(method="POST", path="/rag/query").observe(time.perf_counter() - start)
    return result
