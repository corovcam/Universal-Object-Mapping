#!/bin/bash

cd ../../services/orchestrator || exit 1
source .venv/bin/activate
source .envrc
make dev
