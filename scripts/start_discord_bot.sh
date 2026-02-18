#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${NUMENOR_PATH:-}" ]]; then
  if [[ -d "$HOME/Numenor_Prime" ]]; then
    NUMENOR_PATH="$HOME/Numenor_Prime"
  else
    NUMENOR_PATH="$HOME/Numenor_prime"
  fi
fi

ENV_FILE="${DISCORD_ENV_FILE:-$NUMENOR_PATH/discord_bot/.env}"
ROOT_ENV_FILE="$NUMENOR_PATH/.env"

if [[ -z "${DISCORD_BOT_SCRIPT:-}" ]]; then
  if [[ -f "$NUMENOR_PATH/ATHENA/discord_bot_fixed.py" ]]; then
    BOT_SCRIPT="$NUMENOR_PATH/ATHENA/discord_bot_fixed.py"
  else
    BOT_SCRIPT="$NUMENOR_PATH/athena/discord_bot_fixed.py"
  fi
else
  BOT_SCRIPT="$DISCORD_BOT_SCRIPT"
fi

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
elif [[ -f "$ROOT_ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ROOT_ENV_FILE"
  set +a
fi

exec python "$BOT_SCRIPT"
