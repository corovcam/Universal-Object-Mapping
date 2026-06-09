#!/bin/bash

set -euo pipefail

curl "$DAYTONA_API_URL/snapshots" \
  --request POST \
  --header 'Content-Type: application/json' \
  --header "Authorization: Bearer $DAYTONA_API_KEY" \
  --data '{
  "name": "dotnet-10-sandbox",
  "buildInfo": {
    "dockerfileContent": "FROM mcr.microsoft.com/dotnet/sdk:10.0"
  }
}' | tee /dev/tty | jq '.state' | grep -q "pending" && printf "\nSnapshot 'dotnet-10-sandbox' is being created...\n" || printf "\nSnapshot 'dotnet-10-sandbox' already exists or failed to create.\n"

curl "$DAYTONA_API_URL/snapshots" \
  --request POST \
  --header 'Content-Type: application/json' \
  --header "Authorization: Bearer $DAYTONA_API_KEY" \
  --data '{
  "name": "java-25-sandbox",
  "buildInfo": {
    "dockerfileContent": "FROM bellsoft/liberica-openjdk-debian:25-cds\nRUN apt-get update && apt-get install -y --no-install-recommends maven && rm -rf /var/lib/apt/lists/*\n"
  }
}' | tee /dev/tty | jq '.state' | grep -q "pending" && printf "\nSnapshot 'java-25-sandbox' is being created...\n" || printf "\nSnapshot 'java-25-sandbox' already exists or failed to create.\n"
