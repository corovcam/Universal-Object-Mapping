FROM mcr.microsoft.com/mssql/server:2022-latest

ENV ACCEPT_EULA=Y \
    MSSQL_SA_USER=${MSSQL_SA_USER} \
    MSSQL_SA_PASSWORD=${MSSQL_SA_PASSWORD} \
    MSSQL_USER=${MSSQL_USER} \
    MSSQL_PASSWORD=${MSSQL_PASSWORD} \
    MSSQL_DATABASE=${MSSQL_DATABASE} \
    MSSQL_PID=Developer

WORKDIR /database

USER root
RUN --mount=type=cache,target=/var/lib/apt \
    --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /var/opt/mssql/backup && \
    curl -L -o /var/opt/mssql/backup/WideWorldImporters-Full.bak \
    https://github.com/Microsoft/sql-server-samples/releases/download/wide-world-importers-v1.0/WideWorldImporters-Full.bak

COPY init-db.sh UOM-WideWorldImporters_SQL_SERVER_config.sql ./
RUN chmod +x ./init-db.sh

USER mssql

ENTRYPOINT ["./init-db.sh"]

# Health check to ensure SQL Server is up
HEALTHCHECK --interval=10s --start-period=60s \
    CMD /opt/mssql-tools18/bin/sqlcmd -S localhost -U "${MSSQL_SA_USER:-sa}" -P "${MSSQL_SA_PASSWORD}" -C -Q "SELECT 1" || exit 1
