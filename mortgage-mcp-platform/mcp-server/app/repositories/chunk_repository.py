"""Document chunk persistence."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentChunk


class ChunkRepository:
    """CRUD for chunks."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        document_id: uuid.UUID,
        chunk_index: int,
        content: str,
        metadata: dict[str, Any],
    ) -> DocumentChunk:
        row = DocumentChunk(
            document_id=document_id,
            chunk_index=chunk_index,
            content=content,
            metadata_json=metadata,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def delete_by_document_id(self, document_id: uuid.UUID) -> None:
        await self._session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))

    async def count_for_document(self, document_id: uuid.UUID) -> int:
        from sqlalchemy import func

        q = select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == document_id)
        result = await self._session.execute(q)
        return int(result.scalar_one())
