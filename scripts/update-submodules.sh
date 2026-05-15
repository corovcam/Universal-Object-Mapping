#!/bin/bash

set -euo pipefail

echo "Initializing external repositories..."
git submodule update --init --recursive

echo "Checking and updating submodules..."

for dir in "external/daytona"; do
    echo "Processing $dir..."
    if [ -d "$dir" ]; then
        cd "$dir"
        git fetch --tags
        # Get the latest tag, excluding the current version (if we are on a tag)
        NEXT_TAG=$(git describe --tags --abbrev=0 --exclude=$(git describe --tags --abbrev=0) 2>/dev/null || echo "")
        
        if [ -n "$NEXT_TAG" ]; then
            echo "  -> Found new tag $NEXT_TAG. Checking out..."
            git checkout "$NEXT_TAG"
        else
            echo "  -> No new tags found. Keeping current version."
        fi
        cd ..
    else
        echo "  -> Directory $dir not found. Skipping (this is expected if submodule not initialized)."
    fi
done
