#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${NUMENOR_PATH:-}" ]]; then
  if [[ -d "$HOME/Numenor_Prime" ]]; then
    NUMENOR_PATH="$HOME/Numenor_Prime"
  else
    NUMENOR_PATH="$HOME/Numenor_prime"
  fi
fi

ATHENA_PATH="${ATHENA_PATH:-$NUMENOR_PATH/ATHENA}"
SERVICE_NAME="${ATHENA_DISCORD_SERVICE:-athena-discord-bot.service}"
ENV_FILE="${DISCORD_ENV_FILE:-$NUMENOR_PATH/discord_bot/.env}"
ROOT_ENV_FILE="$NUMENOR_PATH/.env"
START_SCRIPT="$ATHENA_PATH/scripts/start_discord_bot.sh"
LOG_FILE="$NUMENOR_PATH/logs/discord_bot_runtime.log"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
elif [[ -f "$ROOT_ENV_FILE" ]]; then
  set -a
  source "$ROOT_ENV_FILE"
  set +a
fi

printf "== Discord Bot One-Shot Check ==\n"
printf "NUMENOR_PATH: %s\n" "$NUMENOR_PATH"
printf "ATHENA_PATH: %s\n" "$ATHENA_PATH"
printf "Service: %s\n" "$SERVICE_NAME"
printf "DISCORD_BOT_TOKEN set: %s\n" "$( [[ -n "${DISCORD_BOT_TOKEN:-}" ]] && printf YES || printf NO )"
printf "CITADEL_URL: %s\n" "${CITADEL_URL:-http://127.0.0.1:8200}"

for tool in python tmux opencode; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf "Missing required tool: %s\n" "$tool" >&2
    exit 1
  fi
done

if systemctl --user list-unit-files "$SERVICE_NAME" --no-legend 2>/dev/null | grep -q "$SERVICE_NAME"; then
  printf "\nUsing systemd user service path...\n"
  systemctl --user daemon-reload
  systemctl --user restart "$SERVICE_NAME"
  systemctl --user status "$SERVICE_NAME" --no-pager
  printf "\nRecent service logs:\n"
  journalctl --user -u "$SERVICE_NAME" -n 80 --no-pager
else
  printf "\nService not found; using tmux fallback...\n"
  if [[ ! -x "$START_SCRIPT" ]]; then
    chmod +x "$START_SCRIPT"
  fi
  mkdir -p "$NUMENOR_PATH/logs"
  tmux kill-session -t athena-discord-bot 2>/dev/null || true
  tmux new-session -d -s athena-discord-bot "$START_SCRIPT 2>&1 | tee '$LOG_FILE'"
  sleep 2
  tmux has-session -t athena-discord-bot
  printf "tmux session: athena-discord-bot\n"
  printf "runtime log: %s\n" "$LOG_FILE"
  printf "\nRecent runtime logs:\n"
  tail -n 80 "$LOG_FILE" || true
fi

printf "\nDiscord validation steps:\n"
printf "1) Send: !ulw test autonomous loop\n"
printf "2) Wait for completion prompt\n"
printf "3) Reply with plain text task (no !), confirm auto-start\n"
