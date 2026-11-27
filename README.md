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
    sudo wget https://next.hessenbox.de/public.php/dav/files/pD4rKXb7AQCS69H -O ./data/models/models.tar.gz
    sudo tar -xf ./data/models/models.tar.gz --directory ./data/models
    sudo rm -rf ./data/models/models.tar.gz
    sudo chown -R 1000:1000 ./data/
    sudo chmod -R u+rwX ./data/
    sudo chown -R 999:999 "data/shared/db"
    ```

    The plugins load only the checkpoints below, by fixed path under `/models` (= `./data/models`; detector presets in `backend/src/backend/backend/serializers/object_tracker.py`, ReID presets in `serializers/reid_models.py`). [`config/models.sha256`](config/models.sha256) holds their checksums. Check a server or a freshly extracted bundle with:
    ```sh
    (cd ./data/models && sha256sum -c ../../config/models.sha256)
    ```
    A missing or outdated file fails only the runs that pick its preset. Files in `./data/models` that are not listed here are not used.

    | File under `./data/models` | Preset | Size |
    |---|---|---|
    | `yolox/mixsort_yolox_sports_mix.pth.tar` | detector `yolox_sportsmot` (default player detector) | 793 MB |
    | `yolox/bytetrack_x_mot17.pth.tar` | detector `yolox` | 793 MB |
    | `yolox/bytetrack_l_mot17.pth.tar` | detector `yolox_l` | 434 MB |
    | `yolox/bytetrack_x_dancetrack.pth.tar` | detector `yolox_dancetrack` | 793 MB |
    | `yolox/yolox_l-sn-player-coco-ms08-16.pth` | detector `yolox_sn_player` | 434 MB |
    | `yolox/yolox_l-sahi-sn-player.pth` | detector `yolox_sn_player_sahi` (SAHI, 2026-11-19) | 434 MB |
    | `yolox/yolox_l-sahi-sn-ball-native.pth` | detector `yolox_sn_ball` (SAHI, 2026-11-19) | 434 MB |
    | `yolox/yolox_l-sahi-sn-ball-zoom2.pth` | detector `yolox_sn_ball_zoom2` (SAHI) | 434 MB |
    | `yolo_ultra/yolo11x.pt` | detector `yolo11` | 115 MB |
    | `yolo_ultra/yolo11l.pt` | detector `yolo11_l` | 51 MB |
    | `yolo_ultra/yolo11x-sn-player-s05.pt` | detector `yolo11_sn_player` | 114 MB |
    | `rf-detr/rfdetr-l-2026.pth` | detector `rfdetr` | 136 MB |
    | `rf-detr/rfdetr_l-sn-player.pth` | detector `rfdetr_sn_player` | 136 MB |
    | `rf-detr/rfdetr_l-sn-ball.pth` | detector `rfdetr_sn_ball` | 136 MB |
    | `reid/osnet_ain_ms_d_c.pth.tar` | ReID `osnet_ain` (default; also `osnet_reid`, `team_clustering`) | 56 MB |
    | `reid/osnet_x1_0_ms_d_c.pth.tar` | ReID `osnet_x1_0` | 56 MB |
    | `reid/osnet_ibn_ms_d_c.pth.tar` | ReID `osnet_ibn` | 56 MB |
    | `reid/sports_model.pth.tar-60` | ReID `osnet_sportsmot` | 30 MB |
    | `reid/model_soup.deit_l.pth` | ReID `deit_l_sportsreid` | 1547 MB |
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
