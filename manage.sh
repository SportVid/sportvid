#!/bin/bash

ENVIRONMENT=$1
COMMAND=$2

case $ENVIRONMENT in
    "prod"|"production")
        ENV_FILE="/opt/deploy/.env.prod"
        DOCKER_FILE="-f docker-compose.$ENVIRONMENT.yml"
        BRANCH="deploy-prod"
        ;;
    "dev"|"development")
        ENV_FILE="/opt/deploy/.env.dev"
        DOCKER_FILE="-f docker-compose.$ENVIRONMENT.yml"
        BRANCH="deploy-dev"
        ;;
    "shared")
        ENV_FILE="/opt/deploy/.env.db"
        DOCKER_FILE="-f docker-compose.proxy.yml -f docker-compose.db.yml"
        BRANCH="deploy-dev" # TODO: change to deploy-prod later on?!
        ;;
    *)
        echo "Usage: $0 {prod|dev|shared} {build|up|down|restart|logs|shell|migrate}"
        exit 1
        ;;
esac

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    SCRIPT_IS_SOURCED=false
else
    SCRIPT_IS_SOURCED=true
fi

safe_exit() {
    local exit_code=${1:-1}
    if [[ "$SCRIPT_IS_SOURCED" == "true" ]]; then
        echo "Error occurred. Cannot exit when sourced. Returning instead."
        return $exit_code
    else
        exit $exit_code
    fi
}

prepare() {
    local original_dir
    original_dir=$(pwd)

    echo "Executing environment '$ENVIRONMENT' on branch '$BRANCH'"
    
    if ! cd /git/sportvid; then
        echo "Failed to change directory to /git/sportvid"
        safe_exit 1
        return 1
    fi
    
    if ! git checkout "$BRANCH"; then
        echo "Failed to checkout branch: $BRANCH"
        cd "$original_dir" || true
        safe_exit 1
        return 1
    fi
    
    if ! git pull origin "$BRANCH"; then
        echo "Failed to pull from origin: $BRANCH"
        cd "$original_dir" || true
        safe_exit 1
        return 1
    fi
}

exec_docker(){
    local original_dir
    original_dir=$(pwd)
    prepare

    if ! docker compose -p $ENVIRONMENT --env-file $ENV_FILE \
        $DOCKER_FILE \
        $DOCKER_CMD; then
        echo "Running cmd '$DOCKER_CMD' failed..."
        cd "$original_dir" || true
        safe_exit 1
        return 1
    fi
    
    cd "$original_dir" || true
    echo "Done!"
}

case $COMMAND in

    "build")
        DOCKER_CMD="up --build -d"
        echo "Building..."
        exec_docker
        ;;
    "up")
        DOCKER_CMD="up -d"
        echo "Up..."
        exec_docker
        ;;
    "down")
        DOCKER_CMD="down"
        echo "Shutting down..."
        exec_docker
        ;;
    "restart")
        DOCKER_CMD="restart"
        echo "Restarting..."
        exec_docker
        ;;
    "logs")
        DOCKER_CMD="logs -f"
        echo "Logs..."
        exec_docker
        ;;
    "shell")
        DOCKER_CMD="exec backend bash"
        exec_docker
        ;;
    "migrate")
        if [[ "$ENVIRONMENT" == "shared" ]]; then
            echo "Can not migrate shared environment, exiting..."
            safe_exit 1
            return 1
        else
            DOCKER_CMD="exec backend python3 backend/src/backend/manage.py migrate"
	        echo "Migrating..."
            exec_docker
        fi
        ;;
    # NOTE: obsolete since frontend container executes 'npm run build' and copies the file into the shared volume.
    # "frontend-install")
    #     DOCKER_CMD="exec frontend npm install"
    #     echo "Installing npm packages..."
    #     exec_docker
	#     ;;
    # "frontend-build")
	#     DOCKER_CMD="exec frontend npm run build"
    #     echo "Building the frontend..."
	#     exec_docker
    #     ;;
    *)
        echo "Unknown command: $COMMAND"
        safe_exit 1
        ;;
esac