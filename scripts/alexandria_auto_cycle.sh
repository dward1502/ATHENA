#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATHENA_DIR="${ATHENA_PATH:-$(cd "$SCRIPT_DIR/.." && pwd)}"
ALEXANDRIA_ROOT="${ALEXANDRIA_ROOT:-$ATHENA_DIR/../athena-garrison/armoury/alexandria}"
LIMIT="${ALEXANDRIA_CYCLE_LIMIT:-5}"
RETENTION_DAYS="${ALEXANDRIA_RETENTION_DAYS:-14}"

python -m athena.interfaces.alexandria_auto_runner --mode cycle --root "$ALEXANDRIA_ROOT" --limit "$LIMIT"
python -m athena.interfaces.alexandria_auto_runner --mode retention --root "$ALEXANDRIA_ROOT" --retention-days "$RETENTION_DAYS"
