#!/usr/bin/env bash
set -euo pipefail

NUMENOR_PATH="${NUMENOR_PATH:-$HOME/Numenor_prime}"
ENV_FILE="${DISCORD_ENV_FILE:-$NUMENOR_PATH/discord_bot/.env}"
BOT_SCRIPT="${DISCORD_BOT_SCRIPT:-$NUMENOR_PATH/athena/discord_bot_fixed.py}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

exec python "$BOT_SCRIPT"
