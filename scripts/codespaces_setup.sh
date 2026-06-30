#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
fi

mkdir -p .codespaces-data models exports

echo "Trading Cockpit setup complete."
echo "Start with: bash scripts/codespaces_start.sh"
