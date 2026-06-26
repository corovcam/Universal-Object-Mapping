#!/bin/bash

set -euo pipefail

docker compose -f docker-compose.prod.yml down -v --remove-orphans --rmi local
docker compose -f services/daytona/docker-compose.yaml -f docker-compose.prod.daytona.override.yml down -v --remove-orphans --rmi local
