# Cutover Checklist (Laptop -> Main PC)

Use this when promoting work from laptop to main PC runtime.

## 1. Sync Code

```bash
# From main PC
cd ~/Numenor_prime/athena
git pull
```

## 2. Verify Runtime Env

- `~/Numenor_prime/discord_bot/.env` exists
- `DISCORD_BOT_TOKEN` set
- `CORE_API_KEY` set
- `ATHENA_REQUIRE_CORE=1`
- `NUMENOR_PATH` and `ATHENA_GARRISON_PATH` point to main PC paths

## 3. Run Preflight and Smoke

```bash
cd ~/Numenor_prime/athena
./scripts/preflight_check.sh
./scripts/smoke_ready_check.sh
```

## 4. Install/Refresh Systemd Service

```bash
mkdir -p ~/.config/systemd/user
cp ~/Numenor_prime/athena/build_files/systemd/user/athena-discord-bot.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable athena-discord-bot
systemctl --user restart athena-discord-bot
systemctl --user status athena-discord-bot --no-pager
```

## 5. Discord Validation (CEO -> Mystic Architect)

In Discord:

1. `!stack`
2. `!athena run cutover validation`
3. `!sessions`
4. `!log <session-id>`

Expected:

- Stack shows `tmux`, `opencode`, `zeptoclaw`, `picoclaw` present.
- ATHENA mission session is created and progresses.
- Logs show objective intake and deployment output.

## 6. Overnight Readiness Gate

Before overnight autonomous run:

- Service is active and stable for 10+ minutes
- Core-backed ATHENA command succeeds
- Discord command/response loop is healthy
- Claw tools available in runtime (`which zeptoclaw`, `which picoclaw`)

If any gate fails, do not start overnight run.
