#!/bin/bash

set -euo pipefail

# Change directory to the script directory
script_dir=$(dirname -- "$(readlink -f -- "$BASH_SOURCE")")
cd "$script_dir"

timestamp=$(date +"%Y-%m-%d_%H-%M-%S")
mkdir -p logs
log_file="logs/neo4j-etl-tool_$timestamp.log"

# NOTE: Neo4j instance must be stopped first before proceeding with this script
# If you get an error like "WARNING: Neo4j is running! You can run neo4j-import tool only if the database is offline"
# then you need to stop the Neo4j instance first (sometimes twice in a row):
# `neo4j stop`

container_name="universal-object-mapping-neo4j-1"
etl_container_path="/neo4j-etl"
output_dir="$etl_container_path/csv-output/$timestamp"
mssql_jdbc_driver_path="$etl_container_path/sqljdbc_13.4/enu/jars/mssql-jdbc-13.4.0.jre11.jar"

echo "[$(date +"%Y-%m-%d %T")] Starting Neo4j ETL process via docker exec..." |& tee -a "$log_file"

# Copy JDBC driver to ETL lib directory to bypass 'URLClassLoader' ClassCastException in Java 9+
echo "[$(date +"%Y-%m-%d %T")] Adding JDBC driver to ETL classpath..." |& tee -a "$log_file"
docker exec -u 0 -it "$container_name" cp -f "$mssql_jdbc_driver_path" "$etl_container_path/neo4j-etl-cli-1.6.0/lib/"

# Step 1: Export from SQL Server to CSV using neo4j-etl inside the container
echo "[$(date +"%Y-%m-%d %T")] Neo4j ETL Export started" |& tee -a "$log_file"
docker exec -u 0 -w "$etl_container_path" -it "$container_name" ./neo4j-etl-cli-1.6.0/bin/neo4j-etl export \
  --mapping-file mssql_WideWorldImporters_mapping.json \
  --rdbms:password Testingorms123 \
  --rdbms:user sa \
  --rdbms:url "jdbc:sqlserver://mssql_db:1433;databaseName=WideWorldImporters;encrypt=false;trustServerCertificate=true" \
  --options-file import-tool-options.json \
  --using bulk:neo4j-import \
  --csv-directory "$output_dir" \
  --import-tool "/var/lib/neo4j/bin" \
  --destination /data/databases/neo4j/ \
  --force \
  --quote '"' \
  --neo4j:url neo4j://localhost:7687 \
  --neo4j:user neo4j \
  --neo4j:password password 2>&1 | tee -a "$log_file" || {
  echo "[$(date +"%Y-%m-%d %T")] Neo4j ETL Export failed" |& tee -a "$log_file"
}

# The ETL CLI script sometimes eats error codes on failure. Let's explicitly check if output was created.
docker exec -u 0 -it "$container_name" test -d "$output_dir" || {
  echo "[$(date +"%Y-%m-%d %T")] Error: Output directory not created. Export likely failed despite exit code 0." |& tee -a "$log_file"
  exit 1
}

# Step 2: Preprocess the CSV files (remove headers for compatibility with neo4j-admin import)
echo "[$(date +"%Y-%m-%d %T")] Preprocessing import params..." |& tee -a "$log_file"
docker exec -u 0 -it "$container_name" chmod -R 777 "$output_dir"
docker exec -u 0 -it "$container_name" sed -i '1,2d' "$output_dir/csv-001/neo4j-admin-import-params"

# Step 3: Stop the database if possible (required for full bulk import)
# Note: In Community Edition, this may not be supported while keeping the container running.
echo "[$(date +"%Y-%m-%d %T")] Attempting to stop database for import..." |& tee -a "$log_file"
docker exec -u 0 -it "$container_name" neo4j stop 2>&1 | tee -a "$log_file" || echo "[$(date +"%Y-%m-%d %T")] Note: Neo4j database could not be stopped. Continuing anyway..."

# Step 4: Import the CSVs into Neo4j
echo "[$(date +"%Y-%m-%d %T")] Neo4j bulk import started" |& tee -a "$log_file"
docker exec -u 0 -it "$container_name" /var/lib/neo4j/bin/neo4j-admin database import full \
  --verbose \
  --overwrite-destination \
  @"$output_dir/csv-001/neo4j-admin-import-params" 2>&1 | tee -a "$log_file" || {
  echo "[$(date +"%Y-%m-%d %T")] Neo4j bulk import failed" |& tee -a "$log_file"
  exit 1
}
echo "[$(date +"%Y-%m-%d %T")] Neo4j ETL process finished successfully" |& tee -a "$log_file"

# Step 5: Restart the database
echo "[$(date +"%Y-%m-%d %T")] Restarting Neo4j database..." |& tee -a "$log_file"
docker exec -u 0 -it "$container_name" neo4j start 2>&1 | tee -a "$log_file" ||
  docker exec -u 0 -it "$container_name" neo4j restart 2>&1 | tee -a "$log_file" ||
  echo "[$(date +"%Y-%m-%d %T")] Note: Neo4j database could not be re/started. Please restart it manually."
