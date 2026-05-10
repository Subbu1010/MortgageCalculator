"""Smoke tests for the MCP HTTP client package."""

from __future__ import annotations

from mcp_client.client import MortgageClient


def test_from_env_defaults() -> None:
    client = MortgageClient.from_env()
    assert client.base_url.startswith("http")
