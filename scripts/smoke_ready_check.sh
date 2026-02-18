#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATHENA_DIR="${ATHENA_PATH:-$(cd "$SCRIPT_DIR/.." && pwd)}"
NUMENOR_PATH="${NUMENOR_PATH:-$(cd "$ATHENA_DIR/.." && pwd)}"
ATHENA_MODULE="${ATHENA_MODULE:-athena.commander}"
ATHENA_GARRISON_PATH="${ATHENA_GARRISON_PATH:-$NUMENOR_PATH/athena-garrison}"
CORE_API_BASE_URL="${CORE_API_BASE_URL:-https://core.heysol.ai}"
ATHENA_REQUIRE_CORE="${ATHENA_REQUIRE_CORE:-1}"

printf "== ATHENA Smoke Ready Check ==\n"
"$ATHENA_DIR/scripts/preflight_check.sh"

printf "\n== ATHENA status smoke ==\n"
if [[ "$ATHENA_REQUIRE_CORE" == "1" ]]; then
  python -m "$ATHENA_MODULE" --status --garrison-path "$ATHENA_GARRISON_PATH" --core-base-url "$CORE_API_BASE_URL" --require-core >/tmp/athena_smoke_status.txt
else
  python -m "$ATHENA_MODULE" --status --garrison-path "$ATHENA_GARRISON_PATH" --no-require-core >/tmp/athena_smoke_status.txt
fi
printf "[OK] ATHENA status command succeeded\n"

printf "\n== ATHENA mission smoke ==\n"
if [[ "$ATHENA_REQUIRE_CORE" == "1" ]]; then
  python -m "$ATHENA_MODULE" \
    --objective "smoke test discord/core pipeline" \
    --priority HIGH \
    --garrison-path "$ATHENA_GARRISON_PATH" \
    --core-base-url "$CORE_API_BASE_URL" \
    --require-core >/tmp/athena_smoke_mission.txt
else
  python -m "$ATHENA_MODULE" \
    --objective "smoke test discord/core pipeline" \
    --priority HIGH \
    --garrison-path "$ATHENA_GARRISON_PATH" \
    --no-require-core >/tmp/athena_smoke_mission.txt
fi
printf "[OK] ATHENA mission command succeeded\n"

printf "\n== Manual Discord smoke (required) ==\n"
printf "1) Start bot or systemd service\n"
printf "2) In Discord run: !stack\n"
printf "3) In Discord run: !athena smoke test from discord\n"
printf "4) In Discord run: !sessions and !log <session_id>\n"
printf "\nSmoke ready check complete.\n"
