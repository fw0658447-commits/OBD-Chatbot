#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Docker containers:"
docker compose ps || true
echo ""
echo "Backend health:"
curl -s http://localhost:8000/health || true
echo ""
echo ""
echo "Readiness:"
curl -s http://localhost:8000/api/ops/readiness || true
echo ""
