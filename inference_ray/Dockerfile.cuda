FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV PATH="/app/.venv/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    build-essential \
    python3 \
    python3-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.8.4 /uv /uvx /bin/

COPY uv.lock /app/uv.lock
COPY .python-version /app/.python-version
COPY pyproject.toml /app/pyproject.toml

COPY packages/data /app/packages/data
COPY packages/interface /app/packages/interface
COPY packages/utils /app/packages/utils
COPY inference_ray /app/inference_ray

RUN useradd -m -u 1000 appuser \
    && mkdir -p /data /home/appuser/.cache/uv /app \
    && chown -R appuser:appuser /app /data /home/appuser
USER appuser

RUN --mount=type=cache,target=/home/appuser/.cache/uv,uid=1000,gid=1000 \
    uv sync --frozen --no-dev --project /app/inference_ray