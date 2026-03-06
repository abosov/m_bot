#!/usr/bin/env bash

set -e

ROOT="/opt/zumbot/backend"

echo "Cleaning development artifacts..."

echo "Removing __pycache__..."
find "$ROOT" -path "$ROOT/.venv" -prune -o -type d -name "__pycache__" -exec rm -rf {} +

echo "Removing pytest cache..."
find "$ROOT" -name ".pytest_cache" -type d -exec rm -rf {} +

echo "Removing macOS files..."
find "$ROOT" -name ".DS_Store" -delete

echo "Removing Python bytecode..."
find "$ROOT" -name "*.pyc" -delete

echo "Done."
