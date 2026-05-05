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
        BRANCH="deploy-prod"
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

    # ensure we're in a git repo
    if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "Not inside a git repository; aborting."
        safe_exit 1
        return 1
    fi

    # make sure the correct branch is checked out
    if ! git checkout -f "$BRANCH"; then
        echo "Failed to checkout branch: $BRANCH"
        cd "$original_dir" || true
        safe_exit 1
        return 1
    fi

    # update from remote and discard local drift
    if ! git fetch origin; then
        echo "Failed to fetch from origin"
        cd "$original_dir" || true
        safe_exit 1
        return 1
    fi
    
    # resets to remote state in case of local changes
    if ! git reset --hard "origin/$BRANCH"; then
        echo "Failed to reset to origin/$BRANCH"
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
    "rebuild")
        DOCKER_CMD="up --build --force-recreate -d"
        echo "Rebuilding (force recreate)..."
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
    "frontend-install")
        DOCKER_CMD="exec frontend npm install"
        echo "Installing npm packages..."
        exec_docker
	    ;;
    "frontend-build")
	    DOCKER_CMD="exec frontend npm run build"
        echo "Building the frontend..."
	    exec_docker
        ;;
    *)
        echo "Unknown command: $COMMAND"
        safe_exit 1
        ;;
esac