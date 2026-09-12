FROM python:3.11-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /uvx /bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends espeak-ng ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    DATABASE_PATH=/data/rdspan.db \
    AUDIO_PATH=/app/data/audio \
    HOST=0.0.0.0 \
    PORT=8080 \
    PIPER_VOICE=es_ES-davefx-medium \
    PIPER_LENGTH_SCALE=1.35

COPY pyproject.toml uv.lock README.md ./
COPY rdspan ./rdspan
RUN uv sync --frozen --no-dev

COPY data ./data
COPY migrations ./migrations
COPY templates ./templates
COPY static ./static
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && mkdir -p /data

EXPOSE 8081
VOLUME ["/data"]
ENTRYPOINT ["/entrypoint.sh"]
