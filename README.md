# SportVid

**Project website:**
https://sportvid.github.io/

**Prepare for deployment:**
```sh
cd sportvid
sudo mkdir -p /mnt/data/prod/data && cd /mnt/data/prod/data
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
**(Local) Build and start:**
```sh
uv sync
sudo docker compose up --build
```
**(Local) Apply database migrations and build frontend packages:**
```sh
docker compose exec backend python3 backend/src/backend/manage.py migrate
sudo docker compose exec frontend npm install
sudo docker compose exec frontend npm run build
```
**Code reloading:** Hot reloading is enabled for `backend`. To display frontend changes, run:
```sh
sudo docker compose exec frontend npm run build
```
**Alternatively, use `serve` to enable a hot reloaded instance on:**
```sh
sudo docker compose exec frontend npm run serve
```
**(Server) Build an start:**
```sh
./manage.sh prod up  # start the "prod" environment
./manage.sh dev logs  # view "dev" logs
./manage.sh prod shell  # shell into the "prod" backend
./manage.sh dev down  # stop "dev" environment
./manage.sh dev migrate  # apply DB migrations for "dev" environment
./manage.sh prod frontend-install  # install frontend npm packages
./manage.sh prod frontend-build  # build frontend packages
```
