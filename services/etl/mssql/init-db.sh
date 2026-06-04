#!/bin/bash
set -euo pipefail

# Start SQL Server in background
/opt/mssql/bin/sqlservr &
sql_pid=$!

# Wait for SQL Server to accept connections
until /opt/mssql-tools18/bin/sqlcmd -S localhost -U "${MSSQL_SA_USER:-sa}" -P "${MSSQL_SA_PASSWORD:-Testingorms123}" -C -Q "SELECT 1" >/dev/null 2>&1; do
    echo "Waiting for SQL Server to start..."
    sleep 2
done

db_path="/var/opt/mssql/data/WideWorldImporters.mdf"

if [ ! -f "${db_path}" ]; then
    echo "Restoring WideWorldImporters database..."
    /opt/mssql-tools18/bin/sqlcmd -S localhost -U "${MSSQL_SA_USER:-sa}" -P "${MSSQL_SA_PASSWORD:-Testingorms123}" -C \
        -Q "RESTORE DATABASE ${MSSQL_DATABASE:-WideWorldImporters} FROM DISK = '/var/opt/mssql/backup/WideWorldImporters-Full.bak' WITH MOVE 'WWI_Primary' TO '/var/opt/mssql/data/WideWorldImporters.mdf', MOVE 'WWI_UserData' TO '/var/opt/mssql/data/WideWorldImporters_UserData.ndf', MOVE 'WWI_Log' TO '/var/opt/mssql/data/WideWorldImporters.ldf', MOVE 'WWI_InMemory_Data_1' TO '/var/opt/mssql/data/WideWorldImporters_InMemory.ndf';"
else
    echo "WideWorldImporters already present. Skipping restore."
fi

# For MongoDB Relational Migrator
/opt/mssql-tools18/bin/sqlcmd \
  -S localhost \
  -U "${MSSQL_SA_USER:-sa}" \
  -P "${MSSQL_SA_PASSWORD:-Testingorms123}" \
  -C <"${SQL_SERVER_CONFIG_PATH:-UOM-WideWorldImporters_SQL_SERVER_config.sql}"

# Create read-only user for application access
/opt/mssql-tools18/bin/sqlcmd \
  -S localhost \
  -U "${MSSQL_SA_USER:-sa}" \
  -P "${MSSQL_SA_PASSWORD:-Testingorms123}" \
  -d "${MSSQL_DATABASE:-WideWorldImporters}" \
  -C -Q \
  "IF NOT EXISTS (SELECT name FROM sys.database_principals WHERE name = '${MSSQL_USER}') BEGIN CREATE LOGIN [${MSSQL_USER}] WITH PASSWORD = '${MSSQL_PASSWORD:-Uomreadonly123}'; CREATE USER [${MSSQL_USER}] FOR LOGIN [${MSSQL_USER}]; GRANT SELECT TO [${MSSQL_USER}]; END"

# Keep container running
wait "${sql_pid}"
