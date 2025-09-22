#!/bin/bash

ENVIRONMENT=$1
COMMAND=$2

case $ENVIRONMENT in
    "prod"|"production")
        ENV_FILE="/opt/deploy/.env.prod"
        # COMPOSE_FILE="docker-compose.yml:docker-compose.prod.yml"
        BRANCH="deploy-prod"
        ;;
    "dev"|"development")
        ENV_FILE="/opt/deploy/.env.dev"
        # COMPOSE_FILE="docker-compose.yml:docker-compose.dev.yml"
        BRANCH="deploy-dev"
        ;;
    *)
        echo "Usage: $0 {prod|dev} {up|down|restart|logs|shell}"
        exit 1
        ;;
esac

case $COMMAND in
    "up")
        cd /git/sportvid || exit
        git checkout $BRANCH && git pull origin $BRANCH
        docker compose --env-file $ENV_FILE -f docker-compose.$ENVIRONMENT.yml up --build
        # docker compose --env-file $ENV_FILE -f docker-compose.$ENVIRONMENT.yml up -d --build
        ;;
    "down")
        docker compose --env-file $ENV_FILE -f docker-compose.$ENVIRONMENT.yml down
        ;;
    "restart")
        docker compose --env-file $ENV_FILE -f docker-compose.$ENVIRONMENT.yml restart
        ;;
    "logs")
        docker compose --env-file $ENV_FILE -f docker-compose.$ENVIRONMENT.yml logs -f
        ;;
    "shell")
        docker compose --env-file $ENV_FILE -f docker-compose.$ENVIRONMENT.yml exec backend bash
        ;;
    "migrate")
	    cd /git/sportvid || exit
        docker compose --env-file $ENV_FILE -f docker-compose.$ENVIRONMENT.yml exec backend python3 backend/src/backend/manage.py migrate
        ;;
    "frontend-install")
        cd /git/sportvid || exit
        docker compose --env-file $ENV_FILE -f docker-compose.$ENVIRONMENT.yml exec frontend npm install
	    ;;
    "frontend-build")
	    cd /git/sportvid || exit
	    docker compose --env-file $ENV_FILE -f docker-compose.$ENVIRONMENT.yml exec frontend npm run build
        ;;
    *)
        echo "Usage: $0 {prod|dev} {up|down|restart|logs|shell}"
        exit 1
        ;;
esac
