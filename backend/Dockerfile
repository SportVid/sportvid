# For more information, please refer to https://aka.ms/vscode-docker-python
# FROM ubuntu:22.04
FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    wget \
    npm \
    git \
    libsndfile1-dev \
    libmariadbclient-dev-compat \
    imagemagick \
    python3-pip \
    python3-numba \
    python3-opencv \
    python3-psycopg2 \
    python3-numpy \
    python3-sklearn

EXPOSE ${BACKEND_PORT}

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1
ENV NUMBA_CACHE_DIR=/tmp/

WORKDIR /app
COPY . /app

# Switching to a non-root user, please refer to https://aka.ms/vscode-docker-python-user-rights
RUN useradd appuser && chown -R appuser /app
USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
# CMD ["gunicorn", "--bind", "0.0.0.0:5001", "backend:app", "--log-level debug", "--workers=4"]
# CMD ["python", "backend.py"]
