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
    cd sportvid
    sudo mkdir cache
    sudo mkdir analyser
    sudo mkdir media
    sudo mkdir tmp
    sudo mkdir predictions
    sudo mkdir backend_cache
    wget https://next.hessenbox.de/public.php/dav/files/JDnBxSKynARpwWm/?accept=zip -O models.tar.gz
    sudo tar -xf models.tar.gz --directory .
    rm -rf models.tar.gz
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
4. **Apply database migrations and build frontend packages:**
    GPU version (if NVIDIA GPU available):
    ```sh
    sudo docker compose -f docker-compose.cuda.yml up --build
    ```
4. **Apply database migrations and build frontend packages:**
    ```sh
    docker compose exec backend python3 backend/src/backend/manage.py migrate
    sudo docker compose exec frontend npm install
    sudo docker compose exec frontend npm run build
    ```
5. **Code reloading:** 
    Hot reloading is enabled for `backend`. To display the frontend changes, run:
    ```sh
    sudo docker compose exec frontend npm run build
    ```
    Alternatively, use `serve` to enable a hot reloaded instance on:
    ```sh
    sudo docker compose exec frontend npm run serve
    ```
    The frontend instance is accessible via: `http://localhost/8080`.
6. **Debugging:**
    You can directly "move" into a container, e.g. the inference server instance to check the status of plugin execution:
    ```sh
    sudo docker compose exec inference_ray bash
    ray status
    ```
7. **Clean up data:**
    ```sh
    sudo rm -rf ./data/predictions/* \
        ./data/backend_cache/* \
	    ./data/cache/* \
	    ./data/analyser/* \
	    ./data/media/* \
	    ./data/tmp/*
    ```
8. **(Server) Control via management shell script:**
    ```sh
    ./manage.sh <ENV> <CMD>
    ```