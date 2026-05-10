"""Filesystem document ingestion into PostgreSQL pgvector."""

from __future__ import annotations

import asyncio
import hashlib
import mimetypes
from pathlib import Path
import structlog
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import Document
from app.repositories.audit_repository import AuditRepository
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.embedding_repository import EmbeddingRepository

logger = structlog.get_logger(__name__)


def _sha256_head(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:24]


async def ingest_documents_tree(
    session: AsyncSession,
    settings: Settings,
    *,
    base_path: str | None = None,
) -> dict[str, int]:
    """Scan DOCUMENTS_PATH, chunk, embed, and persist."""

    audit = AuditRepository(session)
    documents = DocumentRepository(session)
    chunks_repo = ChunkRepository(session)
    emb_repo = EmbeddingRepository(session)

    root = Path(base_path or settings.documents_path)
    if not root.exists():
        await audit.write(
            action="ingestion_skipped",
            details={"reason": "path missing", "path": str(root)},
        )
        return {"files": 0, "chunks": 0}

    await audit.write(action="ingestion_started", details={"path": str(root)})

    if not settings.google_api_key:
        logger.warning("ingestion_no_api_key", message="Skipping embedding without GOOGLE_API_KEY")
        await audit.write(action="ingestion_partial", details={"reason": "missing GOOGLE_API_KEY"})
        return {"files": 0, "chunks": 0}

    embedder = GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.google_api_key,
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    exts = {".txt", ".md", ".markdown", ".pdf"}
    files_processed = 0
    chunks_total = 0

    walk_files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in exts)

    for path in walk_files:
        rel = str(path.relative_to(root))
        text = _read_document(path)
        if not text.strip():
            continue

        fingerprint = _sha256_head(text)

        existing = await session.execute(
            select(Document).where(
                Document.source_path == rel,
                Document.deleted_at.is_(None),
                Document.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            continue

        doc = await documents.create(
            title=path.stem.replace("_", " ").title(),
            source_path=rel,
            doc_type=path.suffix.lower().lstrip("."),
            metadata={
                "sha256_head": fingerprint,
                "size_bytes": path.stat().st_size,
                "mime": mimetypes.guess_type(rel)[0] or "application/octet-stream",
            },
        )

        splits = splitter.split_text(text)

        chunk_rows = []
        for idx, chunk_text in enumerate(splits):
            ch = await chunks_repo.create(
                document_id=doc.id,
                chunk_index=idx,
                content=chunk_text,
                metadata={"chars": len(chunk_text)},
            )
            chunk_rows.append(ch)

        for ch in chunk_rows:
            vec = (
                await embedder.aembed_query(ch.content)
                if hasattr(embedder, "aembed_query")
                else await asyncio.to_thread(embedder.embed_query, ch.content)
            )
            if len(vec) != settings.embedding_dimensions:
                raise ValueError(
                    f"Embedding dim {len(vec)} != configured {settings.embedding_dimensions}; align model/settings."
                )
            await emb_repo.upsert_for_chunk(
                chunk_id=ch.id,
                model_name=settings.embedding_model,
                dimensions=settings.embedding_dimensions,
                vector=vec,
            )
            chunks_total += 1

        files_processed += 1

    await audit.write(
        action="ingestion_finished",
        details={"files_processed": files_processed, "chunks": chunks_total},
    )
    logger.info("ingestion_complete", files=files_processed, chunks=chunks_total)
    return {"files": files_processed, "chunks": chunks_total}


def _read_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".markdown"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        texts: list[str] = []
        for page in reader.pages:
            t = page.extract_text() or ""
            texts.append(t)
        return "\n".join(texts)
    return ""
