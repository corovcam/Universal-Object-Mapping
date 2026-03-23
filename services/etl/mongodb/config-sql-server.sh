#!/bin/bash

# Ensure script stops on error and treats unset variables as errors
set -euo pipefail

# Use -i to read from stdin, -C to trust server certificate
# Using 'docker compose exec' instead of 'docker exec' to target the service correctly
docker exec -i universal-object-mapping-mssql_db-1 /opt/mssql-tools18/bin/sqlcmd \
  -S localhost \
  -U SA \
  -P "${MSSQL_SA_PASSWORD:-Testingorms123}" \
  -C <"${SQL_SERVER_CONFIG_PATH:-UOM-WideWorldImporters_SQL_SERVER_config.sql}"
