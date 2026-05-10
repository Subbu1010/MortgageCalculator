"""Async HTTP client for mortgage calculation and RAG endpoints."""

from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator

import httpx
from pydantic import BaseModel


class MortgageClient(BaseModel):
    """Configured API client."""

    base_url: str = "http://localhost:8000"
    timeout_seconds: float = 120.0

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def from_env(cls) -> MortgageClient:
        return cls(
            base_url=os.environ.get("MCP_SERVER_BASE_URL", "http://localhost:8000").rstrip("/"),
            timeout_seconds=float(os.environ.get("REQUEST_TIMEOUT_SECONDS", "120")),
        )

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds)

    async def health(self) -> dict[str, Any]:
        async with self._client() as client:
            r = await client.get("/health")
            r.raise_for_status()
            return r.json()

    async def mortgage_calculate(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with self._client() as client:
            r = await client.post("/mortgage/calculate", json=payload)
            r.raise_for_status()
            return r.json()

    async def rag_query(self, query: str, *, top_k: int | None = None, stream: bool = False) -> dict[str, Any]:
        body: dict[str, Any] = {"query": query, "stream": stream}
        if top_k is not None:
            body["top_k"] = top_k
        async with self._client() as client:
            r = await client.post("/rag/query", json=body)
            r.raise_for_status()
            return r.json()

    async def rag_query_stream_sse(self, query: str, *, top_k: int | None = None) -> AsyncIterator[dict[str, Any]]:
        """Yield parsed JSON payloads from chunked SSE replies."""
        body: dict[str, Any] = {"query": query, "stream": True}
        if top_k is not None:
            body["top_k"] = top_k

        async with self._client() as client:
            async with client.stream("POST", "/rag/query", json=body) as response:
                response.raise_for_status()
                async for raw in response.aiter_lines():
                    line = raw.strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data:
                        continue
                    yield json.loads(data)
