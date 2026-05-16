#!/bin/bash

set -euo pipefail

echo "Initializing external repositories..."
git submodule update --init --recursive

echo "Ensuring shared Docker network exists..."
docker network inspect daytona-uom >/dev/null 2>&1 || \
    docker network create daytona-uom
docker network inspect uom >/dev/null 2>&1 || \
    docker network create uom

echo "Starting the stack..."
docker compose up -d --remove-orphans
docker compose -f external/daytona/docker/docker-compose.yaml -f docker-compose.daytona.override.yml up -d --remove-orphans
