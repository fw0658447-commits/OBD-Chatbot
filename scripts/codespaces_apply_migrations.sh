#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Applying PostgreSQL migrations..."
for i in $(seq 1 45); do
  if docker compose exec -T postgres pg_isready -U trading_user -d trading_cockpit >/dev/null 2>&1; then
    break
  fi
  sleep 2
  if [ "$i" = "45" ]; then
    echo "PostgreSQL is not ready." >&2
    exit 1
  fi
done

for f in database/migrations/*.sql; do
  [ -e "$f" ] || continue
  echo "- $f"
  docker compose exec -T postgres psql -U trading_user -d trading_cockpit < "$f" >/dev/null
done

echo "Migrations applied."
