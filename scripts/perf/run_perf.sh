#!/usr/bin/env bash
# scripts/perf/run_perf.sh - Automated Locust benchmark runner for Linux/CI
set -euo pipefail

HOST_URL="${1:-http://localhost:8000}"
DURATION="${2:-60s}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/results"

mkdir -p "$OUTPUT_DIR"

echo "======================================================="
echo "         WarmPath Automated Load Benchmark Suite       "
echo "======================================================="
echo "Target Host: $HOST_URL"
echo "Step Duration: $DURATION"

USER_LEVELS=(50 200 500)
SPAWN_RATES=(10 40 50)

for i in "${!USER_LEVELS[@]}"; do
    USERS="${USER_LEVELS[$i]}"
    RATE="${SPAWN_RATES[$i]}"
    PREFIX="${OUTPUT_DIR}/benchmark_${USERS}_users"

    echo ""
    echo "[*] Starting Benchmark for ${USERS} concurrent users (spawn rate: ${RATE}/s)..."

    locust -f "${SCRIPT_DIR}/locustfile.py" \
        --headless \
        --host "$HOST_URL" \
        --users "$USERS" \
        --spawn-rate "$RATE" \
        --run-time "$DURATION" \
        --csv "$PREFIX" \
        --html "${PREFIX}.html" \
        --only-summary

    echo "[+] Completed test for ${USERS} users. Results saved to ${PREFIX}*.csv"
done

echo ""
echo "[✓] All benchmarks completed successfully. Inspect results in $OUTPUT_DIR"
