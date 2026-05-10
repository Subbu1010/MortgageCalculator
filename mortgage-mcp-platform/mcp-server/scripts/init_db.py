#!/usr/bin/env python3
"""Bootstrap database: wait for PostgreSQL, migrate, optional document ingest."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote_plus

import asyncpg


async def wait_for_postgres(
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    database: str,
    attempts: int = 60,
    delay_seconds: float = 2.0,
) -> None:
    dsn = (
        f"postgresql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{database}"
    )
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            conn = await asyncpg.connect(dsn)
            await conn.close()
            return
        except Exception as exc:  # noqa: BLE001 — startup retry
            last_error = exc
            await asyncio.sleep(delay_seconds)
    raise RuntimeError(f"PostgreSQL unavailable after {attempts} attempts: {last_error}") from last_error


def run_alembic_migrations(base_dir: Path) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(base_dir),
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("Alembic migration failed")


async def startup_ingest() -> None:
    """Run startup ingestion assuming PYTHONPATH includes the server package root."""
    from app.config import get_settings
    from app.db.session import init_engine, session_factory
    from app.services.ingestion_service import ingest_documents_tree

    settings = get_settings()
    if settings.skip_startup_ingest:
        return

    init_engine(settings)
    factory = session_factory()
    async with factory() as session:
        await ingest_documents_tree(session, settings)
        await session.commit()


async def main() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(base_dir))

    from app.config import get_settings

    settings = get_settings()
    await wait_for_postgres(
        host=settings.database_host,
        port=settings.database_port,
        user=settings.database_user,
        password=settings.database_password,
        database=settings.database_name,
    )
    if settings.run_alembic_on_startup:
        run_alembic_migrations(base_dir)
    await startup_ingest()


if __name__ == "__main__":
    asyncio.run(main())
