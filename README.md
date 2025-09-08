# SportVid

## Visit project website
https://sportvid.github.io/

## Development setup


### Requirements
* [docker](https://docs.docker.com/get-docker/)
* [docker-compose](https://docs.docker.com/compose/install/)


### Setup process
1. Clone the TIB-AV-A repository including submodules:
    ```sh
    git clone https://github.com/SportVid/sportvid.git
    cd sportvid
    ```

2. Download and extract models:
    ```sh
    sudo mkdir /mnt/data/dev/data/cache
    sudo mkdir /mnt/data/dev/data/analyser
    sudo mkdir /mnt/data/dev/data/media
    sudo mkdir /mnt/data/dev/data/tmp
    sudo mkdir /mnt/data/dev/data/predictions
    sudo mkdir /mnt/data/dev/data/backend_cache
    cd /mnt/data/dev/data/
    wget https://next.hessenbox.de/public.php/dav/files/JDnBxSKynARpwWm/?accept=zip -O models.tar.gz
    sudo tar -xf models.tar.gz --directory .
    rm -rf models.tar.gz
    ```

3. Build and start the container:
    ```sh
    uv sync
    sudo docker compose up --build
    ```

4. Apply database migrations and build frontend packages:
    ```sh
    docker compose exec backend python3 backend/src/backend/manage.py migrate
    sudo docker compose exec frontend npm install
    sudo docker compose exec frontend npm run build
    ```

5. Go to the frontend instance at `http://localhost/`.

6. Move into container, e.g. inference-server and check status of plugin execution:
    ```
    sudo docker compose exec inference_ray bash
    ray status
    ```

### Code reloading
Hot reloading is enabled for `backend`. To display frontend changes, run:
```sh
sudo docker compose exec frontend npm run build
```
Alternatively, use `serve` to enable a hot reloaded instance on `http://localhost:8080/`:
```sh
sudo docker compose exec frontend npm run serve

```