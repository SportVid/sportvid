# Copilot Instructions for SportVid

## Project Architecture
- **Monorepo structure**: Key components are in `analyser/`, `backend/`, `frontend/`, and `inference_ray/`.
- **Data flow**: Video/media files are processed by plugins (see `analyser/src/analyser/` and `inference_ray/src/inference_ray/plugins/`). Results are stored in `data/predictions/` and `data/media/`.
- **Backend**: Django-based, located in `backend/src/backend/`. Handles API, database, and user management.
- **Frontend**: Vue.js SPA in `frontend/src/`. Communicates with backend via REST API.
- **Plugins**: Custom analysis modules, triggered via scripts or Ray jobs. See `analyser/src/bin/` and `inference_ray/src/inference_ray/plugins/`.

## Developer Workflows
- **Setup**: Use Docker and docker-compose. See `README.md` for step-by-step setup, including model download and extraction.
- **Build/Start**: `uv sync` then `sudo docker compose up --build`.
- **Migrations**: Run Django migrations inside backend container:
  - `sudo docker compose exec backend uv run python3 backend/src/backend/manage.py migrate auth`
  - `sudo docker compose exec backend uv run python3 backend/src/backend/manage.py migrate`
- **Frontend**: Build with `sudo docker compose exec frontend npm run build`. Hot reload enabled.
- **Standalone scripts**: Trigger plugins or export results using scripts in `analyser/src/bin/` (see its README for examples).
- **Ray jobs**: Managed in `inference_ray`. Check status with `ray status` inside the container.

## Conventions & Patterns
- **Plugin execution**: Use provided scripts for consistent job triggering and result export.
- **Data directories**: All persistent data (cache, predictions, media, models) is under `data/`.
- **Container-first**: All commands assume Docker containers; avoid running code directly on host.
- **Model management**: Models are downloaded as a tarball and extracted to `data/`.
- **Frontend/backend separation**: Communicate via API, do not share code directly.

## Integration Points
- **External dependencies**: Docker, docker-compose, Ray, Django, Vue.js.
- **Cross-component communication**: REST API (backend <-> frontend), plugin scripts (analyser/inference_ray <-> backend).
- **Configuration**: See `pyproject.toml` and `config.yml` in each major component for settings.

## Key Files & Directories
- `README.md`: Main setup and workflow guide.
- `analyser/src/bin/README.md`: Plugin script usage.
- `backend/src/backend/manage.py`: Django management.
- `frontend/src/`: Vue.js SPA.
- `inference_ray/src/inference_ray/plugins/`: Ray plugin implementations.
- `data/`: All persistent and model data.

---

For unclear workflows or missing conventions, check the relevant README or ask for clarification. Update this file as new patterns emerge.