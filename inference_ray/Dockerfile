FROM python:3.12-slim-bookworm

WORKDIR /app/analyser/inference/

COPY ./src/ /app/analyser/inference/
COPY ./deploy.yml /app/analyser/deploy.yml

RUN mkdir -p /data

# switch to a non-root user
RUN useradd appuser 
RUN chown -R appuser /data
USER appuser

ENV PYTHONPATH="/app/"

# CMD ["serve", "run", "/app/analyser/deploy.yml"]