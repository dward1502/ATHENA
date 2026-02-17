# Install Guide (BluefinOS, Podman, Main-PC + Laptop)

This is the canonical install/run path for this project.

If you need to ship tonight from laptop to main PC quickly, use:
`docs/setup/FAST_PATH_MAIN_PC_DEPLOY.md`.

## Non-Negotiable Architecture

- `Numenor_prime` on the main PC is the operational company folder.
- Discord is the CEO command channel.
- `OpenCode + oh-my-opencode` is the autonomous execution/control layer.
- ATHENA runs inside `Numenor_prime` and builds/updates CITADEL.
- Runtime targets are resource-constrained (Beelink + Pi5) using Podman pods.
- `picoclaw` + `zeptoclaw` are required for low-RAM operation.
- `RedPlanet Core` is required for persistent memory/context.

## Machine Roles

- Laptop: development, editing, troubleshooting, validation.
- Main PC: authoritative runtime (CEO Discord + ATHENA orchestration).
- Beelink/Pi5: CITADEL pod runtime and demo deployment targets.

## Phase 0 - Baseline Paths

Use these paths consistently:

- Main PC root: `~/Numenor_prime/`
- ATHENA code: `~/Numenor_prime/athena/`
- Discord bot: `~/Numenor_prime/discord_bot/`
- CITADEL runtime: `~/Numenor_prime/citadel/`

## Phase 1 - Main PC Dependencies

Inside Bluefin toolbox on main PC:

```bash
toolbox create athena-dev || true
toolbox enter athena-dev

python -m pip install --upgrade pip
pip install -r ~/Numenor_prime/athena/requirements.txt
pip install discord.py python-dotenv
```

Install required memory/control tooling:

```bash
npm install -g @redplanethq/corebrain
npm install -g opencode oh-my-opencode
# Install your chosen zeptoclaw + picoclaw builds in the same toolbox/runtime
```

Configure Core auth in the runtime environment:

```bash
export CORE_API_KEY=replace_me
# Optional override if self-hosting:
export CORE_API_BASE_URL=https://core.heysol.ai
```

Initialize claw runtimes (verified from upstream docs):

```bash
# ZeptoClaw
zeptoclaw onboard

# PicoClaw
picoclaw onboard
```

Check binaries:

```bash
which zeptoclaw
which picoclaw
```

## Phase 2 - Discord Control Plane

Set bot environment:

```bash
mkdir -p ~/Numenor_prime/discord_bot
cat > ~/Numenor_prime/discord_bot/.env << 'ENV'
DISCORD_BOT_TOKEN=replace_me
ATHENA_PATH=/home/$USER/Numenor_prime/athena
OPENCODE_PATH=/home/$USER/Numenor_prime
NUMENOR_PATH=/home/$USER/Numenor_prime
ATHENA_GARRISON_PATH=/home/$USER/Numenor_prime/athena-garrison
ATHENA_REQUIRE_CORE=1
CORE_API_KEY=replace_me
CORE_API_BASE_URL=https://core.heysol.ai
ATHENA_CORE_SCORE_THRESHOLD=0.35
ATHENA_CORE_TEMPLATE_SCORE_THRESHOLD=0.50
ATHENA_CORE_REFRESH_TIMEOUT=8
REQUIRE_CLAW_STACK=1
ENV
```

Start and validate bot process:

```bash
cd ~/Numenor_prime/athena
python discord_bot_fixed.py
```

Validation:

- In Discord, run `!status` and confirm bot replies.
- In Discord, run `!stack` and confirm `tmux/opencode/zeptoclaw/picoclaw` are present.
- Run a dry request and verify session creation.

Optional one-command preflight on main PC:

```bash
cd ~/Numenor_prime/athena
./scripts/preflight_check.sh
```

Extended smoke check:

```bash
cd ~/Numenor_prime/athena
./scripts/smoke_ready_check.sh
```

OpenCode/oh-my-opencode validation:

- Confirm `opencode --help` runs in the same runtime as the bot.
- Confirm oh-my-opencode config includes ATHENA awareness/hooks.
- Confirm Discord `!ulw ...` path invokes OpenCode end-to-end.

## Phase 2.5 - Systemd User Service (Main PC)

Install service template:

```bash
mkdir -p ~/.config/systemd/user
cp ~/Numenor_prime/athena/build_files/systemd/user/athena-discord-bot.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable athena-discord-bot
systemctl --user restart athena-discord-bot
systemctl --user status athena-discord-bot --no-pager
```

Service launcher script:

- `scripts/start_discord_bot.sh` loads `~/Numenor_prime/discord_bot/.env`
- then starts `discord_bot_fixed.py` from `~/Numenor_prime/athena`

## Phase 3 - ATHENA Runtime Validation

From main PC:

```bash
cd ~/Numenor_prime/athena
python athena.py --objective "sanity build" --deadline "2026-02-19T23:59:59" --priority HIGH
```

Validation:

- Mission ID returns.
- SITREP returns non-empty mission state.
- No hardcoded demo path errors.
- If Core is unavailable, ATHENA exits with explicit error (fail-fast by default).

## Phase 4 - CITADEL Pod Targets (Beelink + Pi5)

Build and export pods from main PC:

```bash
cd ~/Numenor_prime/citadel/pods/plutus-pod
podman build -t plutus:v1.0 .
podman save plutus:v1.0 > plutus-v1.0.tar
```

Transfer and load on Beelink/Pi5:

```bash
scp plutus-v1.0.tar user@beelink:~/containers/
ssh user@beelink 'cd ~/containers && podman load < plutus-v1.0.tar'
```

Repeat for ORACLE/HERMES/APOLLO pods.

## Phase 5 - RedPlanet Core Integration Requirement

ATHENA mission lifecycle must persist to Core memory:

- objective received
- decomposition output
- source repos used
- integration result
- test outcomes
- deployment artifacts

If Core is down, ATHENA should fail fast with explicit error and not pretend success.
API contract details are tracked in: `docs/setup/CORE_INTEGRATION_VERIFIED.md`.

## Phase 6 - Resource-Efficient Runtime Requirement

CITADEL runtime policy:

- Prefer `picoclaw`/`zeptoclaw` execution paths for low RAM.
- Keep only required pods/models live.
- Use queue + priority strategy from coordinator.
- Enforce idle unload/keep-alive policy.

## Known Failure Modes to Check First

- Discord bot connected but no command response: check intents/token/env.
- ATHENA command called but no real execution: check CLI parsing and objective wiring.
- Mission marked complete too early: check completion gating logic.
- Beelink memory pressure: verify pod concurrency policy and model reuse.

## Current Priority Order

1. Make `athena.py` CLI and mission state production-correct.
2. Make `discord_bot_fixed.py` follow the same CLI contract.
3. Connect ATHENA persistence to RedPlanet Core.
4. Wire `picoclaw`/`zeptoclaw` execution paths for constrained runtime.
5. Finalize pod deployment scripts for Beelink/Pi5.
