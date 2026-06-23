FROM ghcr.io/astral-sh/uv:debian

RUN apt-get update && apt-get install -y \
    wget \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV UV_LINK_MODE=copy
ENV PATH="/app/.venv/bin:$PATH"

COPY uv.lock /app/uv.lock
COPY .python-version /app/.python-version
COPY pyproject.toml /app/pyproject.toml
COPY packages/data/pyproject.toml /app/packages/data/pyproject.toml
COPY packages/interface/pyproject.toml /app/packages/interface/pyproject.toml
COPY packages/utils/pyproject.toml /app/packages/utils/pyproject.toml
COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY analyser/pyproject.toml /app/analyser/pyproject.toml
COPY inference_ray/pyproject.toml /app/inference_ray/pyproject.toml

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
# COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENTRYPOINT []
