#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATHENA_DIR="${ATHENA_PATH:-$(cd "$SCRIPT_DIR/.." && pwd)}"
ALEXANDRIA_ROOT="${ALEXANDRIA_ROOT:-$ATHENA_DIR/../athena-garrison/armoury/alexandria}"

python -m athena.interfaces.alexandria_auto_runner --mode status --root "$ALEXANDRIA_ROOT"
