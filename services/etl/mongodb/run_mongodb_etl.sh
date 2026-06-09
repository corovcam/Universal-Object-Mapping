#!/bin/bash

# Change directory to the script directory
script_dir=$(dirname -- "$(readlink -f -- "$BASH_SOURCE")")
cd "$script_dir"

python run_migration.py
