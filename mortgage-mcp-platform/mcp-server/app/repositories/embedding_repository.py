"""Embedding vector persistence and similarity search."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentChunk, Embedding


class EmbeddingRepository:
    """Stores embeddings and runs vector similarity queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_for_chunk(
        self,
        *,
        chunk_id: uuid.UUID,
        model_name: str,
        dimensions: int,
        vector: list[float],
    ) -> Embedding:
        existing = await self._session.execute(select(Embedding).where(Embedding.chunk_id == chunk_id))
        emb = existing.scalar_one_or_none()
        if emb:
            emb.model_name = model_name
            emb.dimensions = dimensions
            emb.embedding = vector
            await self._session.flush()
            return emb
        row = Embedding(
            chunk_id=chunk_id,
            model_name=model_name,
            dimensions=dimensions,
            embedding=vector,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def similarity_search_cosine(
        self,
        query_vector: list[float],
        *,
        top_k: int,
    ) -> list[tuple[DocumentChunk, Document, float]]:
        """Return chunks with parent document ordered by cosine distance (lower is better)."""
        distance_expr = Embedding.embedding.cosine_distance(query_vector)
        stmt: Select[tuple[DocumentChunk, Document, Any]] = (
            select(DocumentChunk, Document, distance_expr.label("distance"))
            .join(Embedding, Embedding.chunk_id == DocumentChunk.id)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                Document.is_active.is_(True),
                Document.deleted_at.is_(None),
                DocumentChunk.deleted_at.is_(None),
            )
            .order_by(distance_expr)
            .limit(top_k)
        )
        result = await self._session.execute(stmt)
        rows = result.all()
        out: list[tuple[DocumentChunk, Document, float]] = []
        for chunk, doc, dist in rows:
            out.append((chunk, doc, float(dist)))
        return out
