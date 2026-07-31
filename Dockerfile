FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# NOTE: better disable post-install .pyc compilation
ENV UV_COMPILE_BYTECODE=0
ENV UV_LINK_MODE=copy

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.8.4 /uv /uvx /bin/

RUN apt-get update && apt-get install -y \
    wget \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY uv.lock pyproject.toml .python-version /app/

COPY packages/data /app/packages/data
COPY packages/interface /app/packages/interface
COPY packages/utils /app/packages/utils
COPY backend /app/backend


ARG UID=1003
ARG GID=1003
RUN groupadd -g ${GID} appuser && \
    useradd -m -u ${UID} -g ${GID} -s /bin/bash appuser

RUN mkdir -p /data /home/appuser/.cache/uv /app \
    && chown -R ${UID}:${GID} /app /data /home/appuser

USER appuser

# Install dependencies first (best practice for caching)
# COPY packages/data/pyproject.toml /app/packages/data/pyproject.toml
# COPY packages/interface/pyproject.toml /app/packages/interface/pyproject.toml
# COPY packages/utils/pyproject.toml /app/packages/utils/pyproject.toml
# COPY backend/pyproject.toml /app/backend/pyproject.toml

RUN --mount=type=cache,target=/home/appuser/.cache/uv,uid=${UID},gid=${GID} \
    uv sync --frozen --no-dev --no-install-workspace --package backend

# Copy only the source actually needed by backend

# COPY analyser/pyproject.toml /app/analyser/pyproject.toml
# COPY inference_ray/pyproject.toml /app/inference_ray/pyproject.toml

# Install just the backend package into the existing environment
# RUN --mount=type=cache,target=/root/.cache/uv \
#     uv sync --frozen --no-dev --package backend

# Ensure .venv is writable by appuser
# RUN chown -R appuser:appuser /app

# Set PATH to use the venv
ENV PATH="/app/.venv/bin:$PATH"

# Adjust entrypoint for your actual app
ENTRYPOINT []