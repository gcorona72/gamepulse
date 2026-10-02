# Imagen ligera para los servicios de ingesta (sin Spark).
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_HTTP_TIMEOUT=300 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock README.md ./
# 1) Solo dependencias: esta capa se cachea y no se repite al cambiar el código
RUN uv sync --frozen --no-dev --no-install-project
# 2) El código del proyecto (rápido, sin descargas)
COPY src ./src
COPY config ./config
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "-m", "gamepulse.ingestion.twitch_producer"]
