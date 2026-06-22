#!/bin/bash

set -u

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    SCRIPT_IS_SOURCED=false
else
    SCRIPT_IS_SOURCED=true
fi

usage() {
    echo "Usage: $0 {prod|production|dev|development|shared} {build|rebuild|up|down|restart|logs|shell|migrate|frontend-install|frontend-build|wipe}"
}

safe_exit() {
    local exit_code=${1:-1}
    if [[ "$SCRIPT_IS_SOURCED" == "true" ]]; then
        echo "Error occurred. Cannot exit when sourced. Returning instead."
        return "$exit_code"
    else
        exit "$exit_code"
    fi
}

die() {
    echo "$1" >&2
    safe_exit "${2:-1}"
}

ENVIRONMENT="${1:-}"
COMMAND="${2:-}"

ENV_NAME=""
ENV_FILE=""
BRANCH=""
DOCKER_FILES=()

case $ENVIRONMENT in
    "prod"|"production")
        ENV_NAME="prod"
        ENV_FILE="/opt/deploy/.env.prod"
        BRANCH="deploy-prod"
        DOCKER_FILES=(-f "docker-compose.prod.yml")
        ;;
    "dev"|"development")
        ENV_NAME="dev"
        ENV_FILE="/opt/deploy/.env.dev"
        BRANCH="deploy-dev"
        DOCKER_FILES=(-f "docker-compose.dev.yml")
        ;;
    "shared")
        ENV_NAME="shared"
        ENV_FILE="/opt/deploy/.env.db"
        BRANCH="deploy-prod"
        DOCKER_FILES=(-f "docker-compose.proxy.yml" -f "docker-compose.db.yml")
        ;;
    *)
        usage
        safe_exit 1
        ;;
esac

prepare() {
    echo "Executing environment '$ENVIRONMENT' on branch '$BRANCH'"
    # ensure we're in a git repo
    git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "Not inside a git repository; aborting."
    # make sure the correct branch is checked out
    git checkout -f "$BRANCH" || die "Failed to checkout branch: $BRANCH"
    # update from remote and discard local drift
    git fetch origin || die "Failed to fetch from origin"
    # resets to remote state in case of local changes
    git reset --hard "origin/$BRANCH" || die "Failed to reset to origin/$BRANCH"
}

run_docker(){
    local -a docker_cmd=("$@")

    prepare || return $?    

    docker compose \
        -p "$ENV_NAME" \
        --env-file "$ENV_FILE" \
        "${DOCKER_FILES[@]}" \
        "${docker_cmd[@]}" || die "Running docker compose command failed."

    echo "Done!"
}

wipe_environment() {
    local base
    local d
    local target

    case "$ENVIRONMENT" in
        prod|production|dev|development)
            ;;
        *)
            die "Invalid environment for wipe: $ENVIRONMENT"
            ;;
    esac

    base="/mnt/data/${ENV_NAME}/data"

    [[ -d "$base" ]] || die "Refusing to wipe: base directory does not exist: $base"

    for d in predictions backend_cache cache analyser media tmp; do
        target="${base}/${d}"

        if [[ -d "$target" ]]; then
            sudo find "$target" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
        else
            echo "Skipping missing directory: $target"
        fi
    done

    echo "Wipe completed for '$ENV_NAME'."
}

main() {
    case $COMMAND in
        "build")
            echo "Building..."
            run_docker up --build -d
            ;;
        "rebuild")
            echo "Rebuilding (force recreate)..."
            run_docker up --build --force-recreate -d
            ;;
        "up")
            echo "Up..."
            run_docker up -d
            ;;
        "down")
            echo "Shutting down..."
            run_docker down
            ;;
        "restart")
            echo "Restarting..."
            run_docker restart
            ;;
        "logs")
            echo "Logs..."
            run_docker logs -f
            ;;
        "shell")
            run_docker exec backend bash
            ;;
        "migrate")
            if [[ "$ENVIRONMENT" == "shared" ]]; then   
                die "Cannot migrate shared environment."
            fi
            echo "Migrating..."
            run_docker exec backend python3 backend/src/backend/manage.py migrate
            ;;
        "frontend-build")
            echo "Building frontend packages..."
            run_docker build frontend
            run_docker up --no-deps frontend
            ;;
        "frontend-rebuild")
            echo "Rebuilding frontend packages..."
            run_docker build --no-cache frontend
            run_docker up --no-deps frontend
            ;;
        "wipe")
            wipe_environment
            ;;
        *)
            echo "Unknown command: $COMMAND"
            usage
            safe_exit 1
            ;;
    esac
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
    main "$@"
fi