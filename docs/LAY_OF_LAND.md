# ATHENA Lay of the Land

This is the current high-level map of the repository, organized for staged analysis.

## Top-Level Structure

- `athena.py` - Core mission orchestration engine and command interface.
- `apollo.py`, `ares.py`, `artemis.py` - Olympian divisions and Titan execution logic.
- `github_scout.py` - Repository reconnaissance and component discovery.
- `code_integrator.py` - Fragment merge, conflict handling, and integration reporting.
- `citadel_pod_coordinator.py` - Lightweight pod scheduler/runtime coordinator.
- `discord_bot_fixed.py` - Discord command interface and session orchestration.
- `demo_integration.py`, `full_system_demo.py` - Demonstration entry points.
- `ceo_athena_bridge.py` - Small CEO-facing bridge wrapper.
- `distributed.py`, `model_manager.py`, `models.py` - Model/node routing prototypes and config notes.
- `olympians/base.py` - Minimal base type.
- `plutus-pod-containerfile` - Container build spec for pod deployment.
- `requirements.txt` - Python dependencies.
- `docs/` - Architecture/setup/integration documentation.

## Operational Constraints

- Runtime is BluefinOS + Podman pods on constrained hardware.
- `picoclaw` + `zeptoclaw` are required (RAM efficiency is mandatory).
- `RedPlanet Core` is required (persistent memory/context).
- `OpenCode + oh-my-opencode` is required for autonomous command execution.
- Main operational path is `~/Numenor_prime` on the main PC.
- Discord is the CEO control channel.

## Documentation Structure

- `docs/architecture/`
  - `CITADEL_COORDINATOR.md`
  - `DOCUMENTATION_CENTER.md`
  - `NUMENOR_INTEGRATION.md`
- `docs/integration/`
  - `DISCORD_ATHENA_INTEGRATION.md`
- `docs/setup/`
  - `CONFIGINSTALL.md`
  - `INSTALL.md`
- `docs/operations/`
  - `DISCORDFIX.md`
- `docs/notes/`
  - `CEO_BOOTSTRAP.md` (currently empty)

## File Size Snapshot (Python)

- Small helpers/prototypes (<= 100 LOC): `ceo_athena_bridge.py`, `distributed.py`, `model_manager.py`, `models.py`, `olympians/base.py`
- Medium modules (100-450 LOC): `demo_integration.py`, `full_system_demo.py`, `citadel_pod_coordinator.py`, `discord_bot_fixed.py`
- Large core modules (450+ LOC): `apollo.py`, `ares.py`, `artemis.py`, `github_scout.py`, `code_integrator.py`, `athena.py`

## Recommended Deep-Dive Order

1. `athena.py` (core domain model and orchestration)
2. `apollo.py`, `ares.py`, `artemis.py` (division behavior)
3. `github_scout.py` and `code_integrator.py` (recon + merge workflow)
4. `citadel_pod_coordinator.py` and `discord_bot_fixed.py` (runtime interfaces)
5. `demo_integration.py`, `full_system_demo.py` (execution paths)
6. `distributed.py`, `model_manager.py`, `models.py`, `ceo_athena_bridge.py`, `olympians/base.py` (support/prototype layer)
7. `requirements.txt`, `plutus-pod-containerfile`, then docs set

## Notes

- Python imports are currently written for a flat top-level module layout.
- Code files were intentionally left in place to avoid breaking import paths before analysis/refactor.
- Canonical setup guide: `docs/setup/INSTALL_CLEAR_BLUEFIN.md`.
