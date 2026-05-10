FROM python:3.12-slim-bookworm

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY mcp_client /app/mcp_client
COPY scripts /app/scripts

RUN groupadd -r -g 1002 clientuser \
    && useradd -r -u 1002 -g clientuser -s /sbin/nologin clientuser \
    && chown -R clientuser:clientuser /app

USER 1002

CMD ["sleep", "infinity"]
