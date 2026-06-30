#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
fi

# v1.5: default to free online market data and same-origin frontend proxy.
grep -q '^MARKET_DATA_PROVIDER=' .env && sed -i 's/^MARKET_DATA_PROVIDER=.*/MARKET_DATA_PROVIDER=free/' .env || echo 'MARKET_DATA_PROVIDER=free' >> .env
grep -q '^NEXT_PUBLIC_API_BASE_URL=' .env && sed -i 's#^NEXT_PUBLIC_API_BASE_URL=.*#NEXT_PUBLIC_API_BASE_URL=auto#' .env || echo 'NEXT_PUBLIC_API_BASE_URL=auto' >> .env

echo "Starting Trading Cockpit with Docker Compose..."
docker compose up -d --build

bash scripts/codespaces_apply_migrations.sh || true

for i in $(seq 1 30); do
  if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo ""
echo "Services are starting. In GitHub Codespaces, open the Ports tab:"
echo "- Port 3000: Frontend"
echo "- Port 8000: API; add /docs for Swagger"
echo ""
echo "v1.5 uses a same-origin frontend proxy: /api/backend -> backend:8000"
echo "Useful checks:"
echo "  bash scripts/codespaces_status.sh"
echo "  bash scripts/codespaces_smoke_test.sh"
echo "  bash scripts/codespaces_full_fix.sh"
