# SportVid

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
    mkdir data/cache
    mkdir data/analyser
    mkdir data/media
    mkdir data/tmp
    mkdir data/predictions
    mkdir data/backend_cache
    wget https://tib.eu/cloud/s/kAe3TXPfsBpwtwk/download/models.tar.gz
    tar -xf models.tar.gz --directory data/
    ```

3. Build and start the container:
    ```sh
    sudo docker-compose up --build
    ```

4. Apply database migrations and build frontend packages:
    ```sh
    sudo docker-compose exec backend python3 manage.py migrate auth
    sudo docker-compose exec backend python3 manage.py migrate
    sudo docker-compose exec frontend npm install
    sudo docker-compose exec frontend npm run build
    ```

5. Go to the frontend instance at `http://localhost/`.


### Code reloading
Hot reloading is enabled for `backend`. To display frontend changes, run:
```sh
sudo docker-compose exec frontend npm run build
```
Alternatively, use `serve` to enable a hot reloaded instance on `http://localhost:8080/`:
```sh
sudo docker-compose exec frontend npm run serve
```

### HowTos/Docs/ToDos
* [How to Add New Backend Functionality in Django](docs/DJANGO_MODEL_VIEW.md)
* [How to Create a New Plugin](docs/PLUGIN_CREATE.md)
* [autocompile protobuf grpc](docs/TODO.md)
