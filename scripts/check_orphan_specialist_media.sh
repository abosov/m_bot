#!/usr/bin/env bash

set -e

BASE="/opt/zumbot/backend/specialist"

echo "Scanning specialist media folders..."

for dir in "$BASE"/*; do
    [ -d "$dir" ] || continue
    id=$(basename "$dir")

    exists=$(sudo -u postgres psql -d zumbot -t -c "SELECT 1 FROM specialist WHERE specialist_id='$id';" 2>/dev/null | tr -d ' ')

    if [ "$exists" != "1" ]; then
        echo "ORPHAN MEDIA: $dir"
    fi
done

echo "Done."
