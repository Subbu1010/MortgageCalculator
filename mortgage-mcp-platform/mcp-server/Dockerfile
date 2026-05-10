FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="mortgage-mcp-server" \
      org.opencontainers.image.description="FastAPI mortgage calculator and pgvector RAG MCP platform"

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic
COPY app /app/app
COPY scripts /app/scripts
COPY startup.sh /app/startup.sh

RUN groupadd -r -g 1001 appuser \
    && useradd -r -u 1001 -g appuser -s /sbin/nologin appuser \
    && chown -R appuser:appuser /app \
    && chmod +x /app/startup.sh

USER 1001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

ENTRYPOINT ["/bin/sh","/app/startup.sh"]
