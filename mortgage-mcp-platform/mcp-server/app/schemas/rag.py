"""RAG API models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    """Citation to an internal document chunk."""

    document_id: str
    document_title: str
    chunk_id: str
    chunk_index: int
    similarity_distance: float
    excerpt: str


class RAGQueryRequest(BaseModel):
    """User query for retrieval augmented generation."""

    query: str = Field(..., min_length=1, max_length=8000)
    top_k: int | None = Field(default=None, ge=1, le=50)
    stream: bool = Field(default=False, description="If true, HTTP response streams tokens when supported")


class RAGQueryResponse(BaseModel):
    """LLM answer with citations."""

    answer: str
    sources: list[SourceReference]
    model_used: str
