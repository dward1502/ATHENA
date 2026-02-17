# ATHENA Progress

Date: 2026-02-16
Status: Active hardening

## Operational Goal

- Discord (CEO) -> OpenCode/oh-my-opencode -> ATHENA -> CITADEL build/deploy flow
- Mandatory runtime stack: picoclaw + zeptoclaw + RedPlanet Core
- BluefinOS + Podman constrained runtime compatibility

## Completed

- ATHENA CLI is production-callable (`athena.py`)
  - objective/deadline/priority flags
  - strict Core mode (`--require-core`) and explicit test override (`--no-require-core`)
- RedPlanet Core integrated for mission lifecycle persistence
  - objective received
  - battle plan created
  - deployment started
  - mission completed
- Core-backed retrieval integrated into planning
  - retrieval before decomposition
  - confidence thresholds
  - template extraction/merge from memory
  - priority weighting from retrieved context
  - ingestion refresh function before planning
- Discord bot hardened (`discord_bot_fixed.py`)
  - env loading support
  - strict stack checks (tmux/opencode/zeptoclaw/picoclaw)
  - Core-aware ATHENA invocation flags
  - `!stack` readiness command
- Operational scripts added
  - `scripts/preflight_check.sh`
  - `scripts/smoke_ready_check.sh`
  - `scripts/start_discord_bot.sh`
- Systemd template added
  - `build_files/systemd/user/athena-discord-bot.service`
- Cutover and setup docs updated
  - `docs/setup/INSTALL_CLEAR_BLUEFIN.md`
  - `docs/setup/CUTOVER_CHECKLIST_MAIN_PC.md`
  - `docs/setup/CORE_INTEGRATION_VERIFIED.md`

## Remaining Gaps (High Priority)

- HERMES/HEPHAESTUS are still fallback-routed to existing divisions
  - functional but not full intended architecture
- Several legacy docs still contain design-draft content
  - now marked as legacy, but full rewrite cleanup still pending
- End-to-end smoke requires live Discord token + Core credentials on main PC

## Next Actions

1. Implement concrete HERMES and HEPHAESTUS modules (minimal functional first pass).
2. Run full main-PC cutover (`preflight` + `smoke` + systemd + Discord command validation).
3. Freeze canonical operator docs and archive outdated drafts.

## Deployment Preference (Operator Confirmed)

- Primary promotion path: GitHub push from laptop, then `git pull` on main PC.
- Operational launch on main PC via OpenCode Sisyphus (`ulw`) after pull.
- `scripts/sync_to_main_pc.sh` remains available as fallback/direct-sync path.

## Ready-to-Use Gate

System is considered ready for overnight use when all pass:

- `./scripts/preflight_check.sh` passes on main PC
- `./scripts/smoke_ready_check.sh` passes on main PC
- Discord commands work (`!stack`, `!athena ...`, `!sessions`, `!log ...`)
- Core-required mode succeeds (`ATHENA_REQUIRE_CORE=1`)
