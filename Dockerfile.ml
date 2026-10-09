# syntax=docker/dockerfile:1
# Imagen de inferencia del modelo de sentimiento (CPU). Solo lo necesario: torch, transformers, duckdb.
# El modelo NO va dentro: Airflow monta models/sentiment al ejecutar.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
ENV UV_HTTP_TIMEOUT=300 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_SYSTEM_PYTHON=1 \
    PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system "torch==2.14.1" --index-url https://download.pytorch.org/whl/cpu
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system "transformers==5.18.0" "tokenizers==0.23.2" "sentencepiece==0.2.2" \
    "protobuf==6.33.6" "duckdb==1.5.6" "pandas==3.0.6" numpy
COPY src ./src
ENV PYTHONPATH=/app/src
CMD ["python", "-m", "gamepulse.ml.predict_sentiment"]
