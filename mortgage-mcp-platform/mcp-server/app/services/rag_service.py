"""Retrieval augmented generation over internal mortgage documents."""

from __future__ import annotations

import asyncio
import uuid

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from app.config import Settings
from app.repositories.audit_repository import AuditRepository
from app.repositories.embedding_repository import EmbeddingRepository
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse, SourceReference


class RAGService:
    """Embedding retrieval and grounded answer synthesis."""

    def __init__(
        self,
        *,
        settings: Settings,
        embeddings: EmbeddingRepository,
        audit: AuditRepository,
    ) -> None:
        self._settings = settings
        self._embeddings = embeddings
        self._audit = audit

    async def query(self, payload: RAGQueryRequest) -> RAGQueryResponse:
        await self._audit.write(
            action="rag_query",
            actor="api",
            resource_type="query",
            resource_id=str(uuid.uuid4()),
            details={"query_length": len(payload.query)},
        )

        if not self._settings.google_api_key:
            return RAGQueryResponse(
                answer=(
                    "Google API key is not configured. Set GOOGLE_API_KEY for embeddings and "
                    "generative responses."
                ),
                sources=[],
                model_used="none",
            )

        embedder = GoogleGenerativeAIEmbeddings(
            model=self._settings.embedding_model,
            google_api_key=self._settings.google_api_key,
        )

        if hasattr(embedder, "aembed_query"):
            qvec = await embedder.aembed_query(payload.query)
        else:
            qvec = await asyncio.to_thread(embedder.embed_query, payload.query)

        top_k = payload.top_k or self._settings.rag_top_k
        rows = await self._embeddings.similarity_search_cosine(qvec, top_k=top_k)

        filtered = [(c, d, dist) for c, d, dist in rows if dist <= self._settings.rag_similarity_threshold]
        if not filtered:
            filtered = list(rows)

        context_blocks: list[str] = []
        sources: list[SourceReference] = []
        for chunk, doc, dist in filtered:
            excerpt = chunk.content[:1200]
            context_blocks.append(f"Title: {doc.title}\nSource: {doc.source_path}\nContent:\n{chunk.content}\n")
            sources.append(
                SourceReference(
                    document_id=str(doc.id),
                    document_title=doc.title,
                    chunk_id=str(chunk.id),
                    chunk_index=chunk.chunk_index,
                    similarity_distance=float(dist),
                    excerpt=excerpt,
                )
            )

        context_text = "\n---\n".join(context_blocks) if context_blocks else "No matching chunks were retrieved."

        llm = ChatGoogleGenerativeAI(
            model=self._settings.gemini_model,
            google_api_key=self._settings.google_api_key,
            temperature=0.2,
        )
        prompt = (
            "You are a mortgage banking assistant. Answer using ONLY the provided internal excerpts. "
            "If the excerpts do not contain enough information, state what is missing. "
            "Reference document titles when stating policies.\n\n"
            f"### Context\n{context_text}\n\n### Question\n{payload.query}"
        )
        if hasattr(llm, "ainvoke"):
            result = await llm.ainvoke(prompt)
        else:
            result = await asyncio.to_thread(llm.invoke, prompt)
        text = result.content if hasattr(result, "content") else str(result)

        return RAGQueryResponse(answer=str(text), sources=sources, model_used=self._settings.gemini_model)
