#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   MAIN_PC_SSH=user@host ./scripts/sync_to_main_pc.sh
# Optional:
#   REMOTE_ATHENA_PATH=~/Numenor_prime/athena

MAIN_PC_SSH="${MAIN_PC_SSH:-}"
REMOTE_ATHENA_PATH="${REMOTE_ATHENA_PATH:-~/Numenor_prime/athena}"

if [[ -z "$MAIN_PC_SSH" ]]; then
  echo "[ERR] MAIN_PC_SSH is required (example: user@mainrig.local)"
  exit 1
fi

echo "[INFO] Syncing repo to ${MAIN_PC_SSH}:${REMOTE_ATHENA_PATH}"

rsync -a \
  --delete \
  --exclude '.git/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.mypy_cache/' \
  --exclude '.pytest_cache/' \
  ./ "${MAIN_PC_SSH}:${REMOTE_ATHENA_PATH}/"

echo "[OK] Sync complete"
