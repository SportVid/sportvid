FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /opt/ByteTrack

COPY ./third_party/ByteTrack/pyproject.toml ./third_party/ByteTrack/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev
COPY ./third_party/ByteTrack /opt/ByteTrack
RUN uv sync --frozen --no-dev

RUN pip install --no-cache-dir -e .
WORKDIR /app/analyser/inference/
COPY ./src/ /app/analyser/inference/

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    git \
    build-essential \
    ca-certificates \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python3 /usr/bin/python

COPY ./requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip setuptools wheel

RUN pip install --no-cache-dir torch==2.6.0 torchvision==0.21.0 \
    --index-url https://download.pytorch.org/whl/cu124

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY ./src/ /app/analyser/inference/
COPY ./deploy.yml /app/analyser/deploy.yml

RUN mkdir -p /data

RUN useradd -m appuser && chown -R appuser /app /data
USER appuser