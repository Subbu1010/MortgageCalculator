"""Command-line interface for mortgage and RAG calls."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from rich.console import Console
from rich.pretty import pprint

from mcp_client.client import MortgageClient

console = Console()


async def cmd_health(client: MortgageClient) -> None:
    pprint(await client.health())


async def cmd_calc(client: MortgageClient, payload_json: str) -> None:
    payload = json.loads(payload_json)
    pprint(await client.mortgage_calculate(payload))


async def cmd_rag(client: MortgageClient, query: str, top_k: int | None, stream: bool) -> None:
    if stream:
        async for chunk in client.rag_query_stream_sse(query, top_k=top_k):
            console.print_json(data=chunk)
    else:
        pprint(await client.rag_query(query, top_k=top_k))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mortgage MCP HTTP client")
    parser.add_argument(
        "--base-url",
        default=None,
        help="Override MCP_SERVER_BASE_URL",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health", help="GET /health")

    p_calc = sub.add_parser("calc", help="POST /mortgage/calculate")
    p_calc.add_argument("payload", help="JSON string for MortgageCalculateRequest")

    p_rag = sub.add_parser("rag", help="POST /rag/query")
    p_rag.add_argument("query", help="Natural language question")
    p_rag.add_argument("--top-k", type=int, default=None)
    p_rag.add_argument("--stream", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.base_url:
        os.environ["MCP_SERVER_BASE_URL"] = args.base_url

    client = MortgageClient.from_env()

    async def runner() -> None:
        if args.command == "health":
            await cmd_health(client)
        elif args.command == "calc":
            await cmd_calc(client, args.payload)
        elif args.command == "rag":
            await cmd_rag(client, args.query, args.top_k, args.stream)

    asyncio.run(runner())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
