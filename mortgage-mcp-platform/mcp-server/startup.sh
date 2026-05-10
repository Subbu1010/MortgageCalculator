#!/bin/sh
set -e
cd /app
python scripts/init_db.py
exec uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
