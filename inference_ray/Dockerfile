FROM ghcr.io/astral-sh/uv:debian

WORKDIR /app/analyser/inference/

COPY ./src/ /app/analyser/inference/
COPY ./deploy.yml /app/analyser/deploy.yml

RUN mkdir -p /data
# switch to non-root user
RUN useradd appuser 
RUN chown -R appuser /data
USER appuser

ENV PYTHONPATH="/app/"

# run the binary
# CMD ["python3", "/app/src/main.py", "-v"]

# run ray serve
# CMD ["serve", "run", "/app/analyser/deploy.yml"]