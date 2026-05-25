#!/bin/bash

set -euo pipefail

UOM_NETWORK="uom"

echo "Initializing external repositories..."
git submodule update --init --recursive

echo "Ensuring shared Docker network exists..."
docker network inspect "$UOM_NETWORK" >/dev/null 2>&1 || \
    docker network create uom

# Default gateway inside the runner container will be whatever network Docker attaches it to. Here we compute the host-gateway
# If your runner is attached to a specific compose network, use that network name below.
HOST_GW="$(docker network inspect "$UOM_NETWORK" --format '{{(index .IPAM.Config 0).Gateway}}')"
export OUTER_HOST_GATEWAY_IP="$HOST_GW"
echo "Using OUTER_HOST_GATEWAY_IP=$OUTER_HOST_GATEWAY_IP for network $UOM_NETWORK"

echo "Starting the stack..."
docker compose up -d --remove-orphans
docker compose -f external/daytona/docker/docker-compose.yaml -f docker-compose.daytona.override.yml up -d --remove-orphans
