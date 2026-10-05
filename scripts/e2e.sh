#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
port="${GATEWAY_PORT:-8080}"
export GATEWAY_API_KEYS="${GATEWAY_API_KEYS:-demo-key:acme-insurance:voice-agent}"
export GATEWAY_URL="http://127.0.0.1:${port}"
export GATEWAY_API_KEY="${GATEWAY_API_KEY:-demo-key}"

python -m uvicorn gateway.main:create_app --factory --port "$port" --log-level warning &
gateway_pid=$!
trap 'kill "$gateway_pid"' EXIT

for _ in $(seq 1 30); do
    curl -fsS "${GATEWAY_URL}/healthz" > /dev/null 2>&1 && break
    sleep 0.5
done

cd "$root/mcp-server"
npm run --silent build
npm run --silent evals
