# Fast Path Deploy To Main PC (3080 / Numenor Prime)

Use this to push the hardened ATHENA stack from laptop to main PC quickly.

## Preferred Delivery Method (Your Workflow)

- Preferred: push to GitHub from laptop, then pull on main PC.
- Then run OpenCode Sisyphus with `ulw` on main PC.
- Keep `scripts/sync_to_main_pc.sh` as an optional fallback when direct rsync is needed.

## 0. Required env on laptop

- `MAIN_PC_SSH` (example: `you@mainrig.local`)
- Optional: `REMOTE_ATHENA_PATH` (default: `~/Numenor_prime/athena`)

## 1. Sync code to main PC

Option A (preferred): GitHub push/pull

```bash
# Laptop
git add -A
git commit -m "ATHENA fast-path hardening"
git push

# Main PC
cd ~/Numenor_prime/athena
git pull
```

Option B (fallback): direct sync script

```bash
cd /path/to/ATHENA
MAIN_PC_SSH=you@mainrig.local ./scripts/sync_to_main_pc.sh
```

## 2. Ensure main-PC runtime env is ready

On main PC, verify `~/Numenor_prime/discord_bot/.env` includes:

- `DISCORD_BOT_TOKEN`
- `NUMENOR_PATH`
- `ATHENA_GARRISON_PATH`
- `ATHENA_REQUIRE_CORE=1`
- `CORE_API_KEY`
- `CORE_API_BASE_URL`
- `REQUIRE_CLAW_STACK=1`

## 3. Run remote cutover

```bash
cd /path/to/ATHENA
MAIN_PC_SSH=you@mainrig.local ./scripts/remote_cutover_main_pc.sh
```

This runs on main PC:

1. `./scripts/preflight_check.sh`
2. `./scripts/smoke_ready_check.sh`
3. Installs and restarts `athena-discord-bot` systemd user service

## 4. Discord go-live checks

From Discord:

1. `!stack`
2. `!athena run cutover validation for CITADEL` 
3. `!sessions`
4. `!log <session-id>`

## 5. Tonight's operating mode

- Use this fast path for immediate CITADEL work tonight.
- After stable operation, proceed with full path integration (HERMES + HEPHAESTUS + expanded CEO task loop).
