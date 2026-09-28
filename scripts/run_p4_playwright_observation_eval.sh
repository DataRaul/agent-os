#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$ROOT/catalog/p4-playwright-observation-config.json"
SERVER_LOG="$(mktemp)"
SNAPSHOT_OUT="$(mktemp)"
FIND_OUT="$(mktemp)"
CONSOLE_OUT="$(mktemp)"
REQUESTS_OUT="$(mktemp)"

cleanup() {
  playwright-cli --config "$CONFIG" close >/dev/null 2>&1 || true
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
  fi
  rm -f "$SERVER_LOG" "$SNAPSHOT_OUT" "$FIND_OUT" "$CONSOLE_OUT" "$REQUESTS_OUT"
}
trap cleanup EXIT

python "$ROOT/scripts/p4_playwright_fixture_server.py" >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!

for _ in {1..30}; do
  if curl --fail --silent http://127.0.0.1:8765/ >/dev/null; then
    break
  fi
  sleep 0.1
done
curl --fail --silent http://127.0.0.1:8765/ >/dev/null

playwright-cli --config "$CONFIG" open http://127.0.0.1:8765/ >/dev/null
sleep 1
playwright-cli --config "$CONFIG" snapshot >"$SNAPSHOT_OUT"
playwright-cli --config "$CONFIG" find "Runtime Ready" >"$FIND_OUT"
playwright-cli --config "$CONFIG" console >"$CONSOLE_OUT"
playwright-cli --config "$CONFIG" requests >"$REQUESTS_OUT"

grep -F "Runtime Ready" "$SNAPSHOT_OUT" >/dev/null
grep -F "Runtime Ready" "$FIND_OUT" >/dev/null
grep -F "P4_RUNTIME_CONSOLE_ERROR" "$CONSOLE_OUT" >/dev/null
grep -F "/missing" "$REQUESTS_OUT" >/dev/null

if [[ -n "$(git -C "$ROOT" status --porcelain)" ]]; then
  echo "P4_PLAYWRIGHT_OBSERVATION_EVAL_FAIL: repository mutated"
  git -C "$ROOT" status --short
  exit 1
fi

echo "P4_PLAYWRIGHT_OBSERVATION_RUNTIME_EVAL_PASS"
