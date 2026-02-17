#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   MAIN_PC_SSH=user@host ./scripts/remote_cutover_main_pc.sh
# Optional:
#   REMOTE_ATHENA_PATH=~/Numenor_prime/athena

MAIN_PC_SSH="${MAIN_PC_SSH:-}"
REMOTE_ATHENA_PATH="${REMOTE_ATHENA_PATH:-~/Numenor_prime/athena}"

if [[ -z "$MAIN_PC_SSH" ]]; then
  echo "[ERR] MAIN_PC_SSH is required (example: user@mainrig.local)"
  exit 1
fi

ssh "$MAIN_PC_SSH" bash -lc "
set -euo pipefail
cd ${REMOTE_ATHENA_PATH}

# Preflight + smoke
./scripts/preflight_check.sh
./scripts/smoke_ready_check.sh

# Install/reload user service
mkdir -p ~/.config/systemd/user
cp ./build_files/systemd/user/athena-discord-bot.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable athena-discord-bot
systemctl --user restart athena-discord-bot
systemctl --user status athena-discord-bot --no-pager
"

echo "[OK] Remote cutover complete"
