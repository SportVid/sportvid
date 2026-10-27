# SportVid

## Project website
https://sportvid.github.io/

## Development setup

### Requirements
    * [docker](https://docs.docker.com/get-docker/)
    * [docker-compose](https://docs.docker.com/compose/install/)

### Setup process

1. **Clone the repository:**
    ```sh
    git clone https://github.com/SportVid/sportvid.git
    cd sportvid
    ```
2. **Prepare for deployment:**
    ```sh
    sudo mkdir -p ./data/cache
    sudo mkdir -p ./data/analyser
    sudo mkdir -p ./data/media
    sudo mkdir -p ./data/tmp
    sudo mkdir -p ./data/predictions
    sudo mkdir -p ./data/backend_cache
    sudo mkdir -p ./data/models
    sudo wget https://next.hessenbox.de/public.php/dav/files/JDnBxSKynARpwWm/?accept=zip -O ./data/models/models.tar.gz
    sudo tar -xf ./data/models/models.tar.gz --directory ./data/models
    sudo rm -rf ./data/models/models.tar.gz
    sudo chown -R 1000:1000 ./data/
    sudo chmod -R u+rwX ./data/
    sudo chown -R 999:999 "data/shared/db"
    ```
3. **Build and start:**

    Prepare:
    ```sh
    uv sync
    ```
    Start (only CPU):
    ```sh
    sudo docker compose up --build
    ```
    GPU version (if NVIDIA GPU available):
    ```sh
    sudo docker compose -f docker-compose.cuda.yml up --build
    ```
    Force rebuild of specific containers:
    ```sh
    sudo docker compose -f docker-compose.cuda.yml up --no-deps --build --force-recreate <container_name>
    ```
    Force no rebuilds:
    ```sh
    sudo docker compose -f docker-compose.cuda.yml up --no-recreate
    ```
4. **Apply database migrations and build frontend packages:**
    ```sh
    docker compose exec backend python3 backend/src/backend/manage.py migrate
    sudo docker compose exec frontend npm install
    sudo docker compose exec frontend npm run build
    ```
5. **Log in:**

    The backend creates a local admin at every start from `.env` (`DEV_ADMIN_USERNAME`/`DEV_ADMIN_PASSWORD`, default `admin` / `sportvid-dev-admin`). This only works with `ENVIRONMENT=local`. New accounts registered in the UI must be activated by an admin in the admin panel.

6. **Code reloading:**

    The source folders are bind-mounted, but gunicorn and Celery do **not** hot-reload. After backend changes, restart the services:
    ```sh
    sudo docker compose restart backend celery-io celery-gpu
    ```
    To display the frontend changes, run:
    ```sh
    sudo docker compose exec frontend npm run build
    ```
    Alternatively, use `serve` to enable a hot reloaded instance on:
    ```sh
    sudo docker compose exec frontend npm run serve
    ```
    The frontend instance is accessible via: `http://localhost:8080`.

7. **Debugging:**

    You can directly "move" into a container, e.g. the inference server instance to check the status of plugin execution:
    ```sh
    sudo docker compose exec inference_ray bash
    ray status
    ```
8. **Clean up data:**
    ```sh
    sudo rm -rf ./data/predictions/* \
        ./data/backend_cache/* \
	    ./data/cache/* \
	    ./data/analyser/* \
	    ./data/media/* \
	    ./data/tmp/*
    ```

## Tests

The backend has a pytest-django suite in `tests/`. It needs no running containers and runs in CI (`.github/workflows/tests.yml`):
```sh
uv run --package backend --group dev pytest
```

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md): how the platform is built, the adopted target rules (T1–T19) and their status. Decisions are recorded in [docs/adr/](docs/adr/).
- [docs/tutorials/](docs/tutorials/): [STRUCTURE.md](docs/tutorials/STRUCTURE.md) (repo layout), [BACKEND101.md](docs/tutorials/BACKEND101.md) (backend development), [PLUGIN101.md](docs/tutorials/PLUGIN101.md) (adding an analysis plugin).
- [docs/todos/](docs/todos/README.md): open work per area.
