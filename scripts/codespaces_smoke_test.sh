#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Health:"
curl -s http://localhost:8000/health

echo "\nOps status:"
curl -s http://localhost:8000/api/ops/status

echo "\nFull diagnostics:"
curl -s 'http://localhost:8000/api/ops/full-diagnostics?symbol=BTC/USD&timeframe=1h&strategy_name=trend_atr_v0.7'

echo "\nRecommendation:"
curl -s 'http://localhost:8000/api/intelligence/recommendation?symbol=BTC/USD&timeframe=1h&strategy_name=trend_atr_v0.7&include_internet=true'

echo "\nPaper deposit test:"
curl -s -X POST http://localhost:8000/api/portfolio/paper/deposit \
  -H 'Content-Type: application/json' \
  -d '{"amount":1000,"note":"v1.5 smoke test deposit"}'

echo "\nPaper portfolio:"
curl -s http://localhost:8000/api/portfolio/paper

echo ""
