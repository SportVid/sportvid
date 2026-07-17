FROM ghcr.io/astral-sh/uv:debian

RUN apt-get update && apt-get install -y \
    wget \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# Copy only files that affect dependency resolution for this image
COPY uv.lock pyproject.toml .python-version /app/
COPY packages/data/pyproject.toml /app/packages/data/pyproject.toml
COPY packages/interface/pyproject.toml /app/packages/interface/pyproject.toml
COPY packages/utils/pyproject.toml /app/packages/utils/pyproject.toml
COPY backend/pyproject.toml /app/backend/pyproject.toml

# Install dependencies only, not the workspace packages themselves
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace

# Now copy only the source actually needed by backend
COPY packages/data /app/packages/data
COPY packages/interface /app/packages/interface
COPY packages/utils /app/packages/utils
COPY backend /app/backend
COPY analyser/pyproject.toml /app/analyser/pyproject.toml
COPY inference_ray/pyproject.toml /app/inference_ray/pyproject.toml

# Install just the backend package into the existing environment
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package backend

ENTRYPOINT []
