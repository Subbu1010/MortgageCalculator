"""MCP stdio server exposing mortgage and RAG tools."""

from __future__ import annotations

import json
from typing import Any

import anyio
import mcp.types as types
import structlog
from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server

from app.config import get_settings
from app.db.session import init_engine, session_factory
from app.repositories.audit_repository import AuditRepository
from app.repositories.embedding_repository import EmbeddingRepository
from app.schemas.mortgage import MortgageCalculateRequest
from app.schemas.rag import RAGQueryRequest
from app.services.mortgage_service import MortgageService
from app.services.rag_service import RAGService

logger = structlog.get_logger(__name__)


async def handle_list_tools(
    _ctx: ServerRequestContext,
    _params: types.PaginatedRequestParams | None,
) -> types.ListToolsResult:
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name="mortgage_calculate",
                title="Mortgage calculation",
                description="Compute principal and interest, escrow, PMI, and amortization for fixed or ARM loans.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "payload": {
                            "type": "object",
                            "description": "MortgageCalculateRequest matching the REST API schema.",
                        }
                    },
                    "required": ["payload"],
                },
            ),
            types.Tool(
                name="rag_query",
                title="Policy RAG query",
                description="Retrieve internal mortgage banking documents with grounded summaries.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "top_k": {"type": "integer"},
                    },
                    "required": ["query"],
                },
            ),
        ]
    )


async def handle_call_tool(
    _ctx: ServerRequestContext,
    params: types.CallToolRequestParams,
) -> types.CallToolResult:
    arguments: dict[str, Any] = params.arguments or {}

    if params.name == "mortgage_calculate":
        raw = arguments.get("payload")
        if isinstance(raw, str):
            data = json.loads(raw)
        else:
            data = raw
        req = MortgageCalculateRequest.model_validate(data)
        result = MortgageService().calculate(req)
        body = types.TextContent(type="text", text=result.model_dump_json(indent=2))
        return types.CallToolResult(content=[body])

    if params.name == "rag_query":
        settings = get_settings()
        init_engine(settings)
        factory = session_factory()

        async with factory() as session:
            try:
                svc = RAGService(
                    settings=settings,
                    embeddings=EmbeddingRepository(session),
                    audit=AuditRepository(session),
                )
                rag_req = RAGQueryRequest(
                    query=str(arguments.get("query", "")),
                    top_k=arguments.get("top_k"),
                    stream=False,
                )
                out = await svc.query(rag_req)
                await session.commit()
                return types.CallToolResult(
                    content=[types.TextContent(type="text", text=out.model_dump_json(indent=2))]
                )
            except Exception as exc:
                await session.rollback()
                logger.exception("mcp_rag_failed", error=str(exc))
                return types.CallToolResult(
                    content=[types.TextContent(type="text", text=json.dumps({"error": str(exc)}))]
                )

    raise ValueError(f"Unknown MCP tool: {params.name}")


def main() -> int:
    get_settings()
    init_engine(get_settings())

    platform = Server(
        "mortgage-mcp-platform",
        on_list_tools=handle_list_tools,
        on_call_tool=handle_call_tool,
    )

    async def arun() -> None:
        async with stdio_server() as streams:
            await platform.run(streams[0], streams[1], platform.create_initialization_options())

    anyio.run(arun)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
