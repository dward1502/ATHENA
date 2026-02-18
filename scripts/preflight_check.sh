#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATHENA_DIR="${ATHENA_PATH:-$(cd "$SCRIPT_DIR/.." && pwd)}"
NUMENOR_PATH="${NUMENOR_PATH:-$(cd "$ATHENA_DIR/.." && pwd)}"
ATHENA_MODULE="${ATHENA_MODULE:-athena.commander}"
ATHENA_MODULE_FILE="$ATHENA_DIR/athena/commander.py"
ATHENA_GARRISON_PATH="${ATHENA_GARRISON_PATH:-$NUMENOR_PATH/athena-garrison}"
CORE_API_BASE_URL="${CORE_API_BASE_URL:-https://core.heysol.ai}"
ATHENA_REQUIRE_CORE="${ATHENA_REQUIRE_CORE:-1}"

ok() { printf "[OK] %s\n" "$1"; }
err() { printf "[ERR] %s\n" "$1"; }

printf "== ATHENA Stack Preflight ==\n"
printf "NUMENOR_PATH=%s\n" "$NUMENOR_PATH"
printf "ATHENA_DIR=%s\n" "$ATHENA_DIR"

for bin in python tmux opencode zeptoclaw picoclaw; do
  if command -v "$bin" >/dev/null 2>&1; then
    ok "binary present: $bin -> $(command -v "$bin")"
  else
    err "binary missing: $bin"
    exit 1
  fi
done

if [[ -f "$ATHENA_MODULE_FILE" ]]; then
  ok "ATHENA module entrypoint found: $ATHENA_MODULE_FILE"
else
  err "ATHENA module entrypoint missing: $ATHENA_MODULE_FILE"
  exit 1
fi

OMOC_CONFIG="$HOME/.config/opencode/oh-my-opencode.json"
if [[ -f "$OMOC_CONFIG" ]]; then
  ok "oh-my-opencode config present: $OMOC_CONFIG"
else
  err "oh-my-opencode config missing: $OMOC_CONFIG"
  exit 1
fi

if [[ -n "${DISCORD_BOT_TOKEN:-}" ]]; then
  ok "DISCORD_BOT_TOKEN is set"
else
  err "DISCORD_BOT_TOKEN is not set"
  exit 1
fi

if [[ "$ATHENA_REQUIRE_CORE" == "1" ]]; then
  if [[ -z "${CORE_API_KEY:-}" ]]; then
    err "CORE_API_KEY missing while ATHENA_REQUIRE_CORE=1"
    exit 1
  fi
  ok "CORE_API_KEY is set"
fi

mkdir -p "$ATHENA_GARRISON_PATH"
ok "garrison path writable: $ATHENA_GARRISON_PATH"

if [[ "$ATHENA_REQUIRE_CORE" == "1" ]]; then
  python -m "$ATHENA_MODULE" --status --garrison-path "$ATHENA_GARRISON_PATH" --core-base-url "$CORE_API_BASE_URL" --require-core >/tmp/athena_preflight_status.txt
else
  python -m "$ATHENA_MODULE" --status --garrison-path "$ATHENA_GARRISON_PATH" --no-require-core >/tmp/athena_preflight_status.txt
fi
ok "ATHENA status command succeeded"

printf "\nPreflight complete.\n"
