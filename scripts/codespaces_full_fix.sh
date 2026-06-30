#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

git config --global --add safe.directory "$(pwd)" || true

if [ ! -f .env ]; then
  cp .env.example .env
fi

# Force v1.5 safe defaults for iPad/Codespaces unless the user already edited them.
grep -q '^MARKET_DATA_PROVIDER=' .env && sed -i 's/^MARKET_DATA_PROVIDER=.*/MARKET_DATA_PROVIDER=free/' .env || echo 'MARKET_DATA_PROVIDER=free' >> .env
grep -q '^NEXT_PUBLIC_API_BASE_URL=' .env && sed -i 's#^NEXT_PUBLIC_API_BASE_URL=.*#NEXT_PUBLIC_API_BASE_URL=auto#' .env || echo 'NEXT_PUBLIC_API_BASE_URL=auto' >> .env
grep -q '^MARKET_PROVIDER_FALLBACK_ENABLED=' .env && sed -i 's/^MARKET_PROVIDER_FALLBACK_ENABLED=.*/MARKET_PROVIDER_FALLBACK_ENABLED=true/' .env || echo 'MARKET_PROVIDER_FALLBACK_ENABLED=true' >> .env

chmod +x scripts/*.sh || true

docker compose down || true
docker compose up -d --build
bash scripts/codespaces_apply_migrations.sh

echo "Waiting for backend..."
for i in $(seq 1 45); do
  if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
  if [ "$i" = "45" ]; then
    docker compose logs backend --tail=80
    exit 1
  fi
done

bash scripts/codespaces_smoke_test.sh

echo ""
echo "Full fix complete. Open Ports: 3000 frontend, 8000 API (/docs)."
