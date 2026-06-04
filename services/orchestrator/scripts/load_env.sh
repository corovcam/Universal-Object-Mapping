#!/bin/bash

set -euo pipefail

# Load environment variables from .env.dev
SCRIPT_DIR="$(dirname "$0")"
if [ -f "$SCRIPT_DIR/../.env.dev" ]; then
    set -a
    source "$SCRIPT_DIR/../.env.dev"
    set +a
    echo "Environment variables loaded from $SCRIPT_DIR/../.env.dev"
else
    echo "Warning: .env.dev file not found in $SCRIPT_DIR. No environment variables loaded."
fi