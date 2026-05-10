"""Document persistence."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document


class DocumentRepository:
    """CRUD for documents."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        title: str,
        source_path: str | None,
        doc_type: str | None,
        metadata: dict[str, Any],
    ) -> Document:
        doc = Document(
            title=title,
            source_path=source_path,
            doc_type=doc_type,
            metadata_json=metadata,
        )
        self._session.add(doc)
        await self._session.flush()
        return doc

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        result = await self._session.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()

    async def list_active(self, limit: int = 1000) -> list[Document]:
        q = (
            select(Document)
            .where(Document.is_active.is_(True), Document.deleted_at.is_(None))
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        rows = await self._session.execute(q)
        return list(rows.scalars().all())

    async def soft_delete(self, document_id: uuid.UUID) -> None:
        await self._session.execute(
            update(Document).where(Document.id == document_id).values(is_active=False, deleted_at=func.now())
        )
