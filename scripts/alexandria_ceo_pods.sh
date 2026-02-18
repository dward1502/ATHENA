#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATHENA_DIR="${ATHENA_PATH:-$(cd "$SCRIPT_DIR/.." && pwd)}"
ALEXANDRIA_ROOT="${ALEXANDRIA_ROOT:-$ATHENA_DIR/../athena-garrison/armoury/alexandria}"
QUEUE_MODE="${ALEXANDRIA_POD_QUEUE_MODE:-digest}"
POD_SIZE="${ALEXANDRIA_POD_SIZE:-5}"
MAX_PODS="${ALEXANDRIA_MAX_PODS:-4}"
PAUSE_SECONDS="${ALEXANDRIA_POD_PAUSE_SECONDS:-1}"

python -m athena.interfaces.alexandria_auto_runner \
  --mode pods \
  --root "$ALEXANDRIA_ROOT" \
  --queue-mode "$QUEUE_MODE" \
  --pod-size "$POD_SIZE" \
  --max-pods "$MAX_PODS" \
  --pause-seconds "$PAUSE_SECONDS"
