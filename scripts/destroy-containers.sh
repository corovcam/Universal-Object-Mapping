#!/bin/bash

set -euo pipefail

docker compose down -v --remove-orphans --rmi local
docker compose -f external/daytona/docker/docker-compose.yaml -f docker-compose.daytona.override.yml down -v --remove-orphans --rmi local
