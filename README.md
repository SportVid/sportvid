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
    sudo wget https://next.hessenbox.de/public.php/dav/files/JDnBxSKynARpwWm/?accept=zip -O ./data/models/models.tar.gz
    sudo tar -xf models.tar.gz --directory ./data/models
    sudo rm -rf ./data/models/models.tar.gz
    sudo chown -R 1000:1000 ./data/
    sudo chmod -R u+rwX ./data/
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
5. **Apply database migrations and build frontend packages:**
    ```sh
    docker compose exec backend python3 backend/src/backend/manage.py migrate
    sudo docker compose exec frontend npm install
    sudo docker compose exec frontend npm run build
    ```
6. **Code reloading:** 

    Hot reloading is enabled for `backend`. To display the frontend changes, run:
    ```sh
    sudo docker compose exec frontend npm run build
    ```
    Alternatively, use `serve` to enable a hot reloaded instance on:
    ```sh
    sudo docker compose exec frontend npm run serve
    ```
    The frontend instance is accessible via: `http://localhost/8080`.

8. **Debugging:**

    You can directly "move" into a container, e.g. the inference server instance to check the status of plugin execution:
    ```sh
    sudo docker compose exec inference_ray bash
    ray status
    ```
10. **Clean up data:**
    ```sh
    sudo rm -rf ./data/predictions/* \
        ./data/backend_cache/* \
	    ./data/cache/* \
	    ./data/analyser/* \
	    ./data/media/* \
	    ./data/tmp/*
    ```
11. **(Server) Control via management shell script:**
    ```sh
    ./manage.sh <ENV> <CMD>
    ```