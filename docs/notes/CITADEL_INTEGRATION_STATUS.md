# CITADEL Integration Status

Date: 2026-02-17
Sprint: Feb 15-19 (Demo Thursday Feb 19)
Author: Arandur Prime (CEO Agent)

## Verified State (2026-02-17 01:05 PST)

### CITADEL_BASE (`Eregion/CITADEL_BASE/citadel/`)

**Initialization**: PASSES
- ORACLE, PLUTUS, HERMES agents: ✅ initialized
- WARDEN security (high level): ✅ initialized
- Philosophical validators (Bacon, Plato, Marcus): ✅ initialized
- local_llama via Ollama (nemotron-3-nano): ✅ loaded and available
- anthropic_claude: ✗ no ANTHROPIC_API_KEY in CITADEL .env (fine — local-first)
- Knowledge graph: ✅ loaded
- Audit trail: ✅ ready

**FastAPI Server**: STARTS (tested on port 8200)
- `/health` → `{"ok": true}`
- `/api/process` → POST `{prompt, context, user_id}` → full pipeline response
- `/` → Dashboard (Jinja2)
- `/agent/{name}` → Agent pages with onboarding
- `/voice/route` → Whisper ASR + command routing
- Mission Control router: optional, at port 9100

**Python venv**: `/var/home/dward/Eregion/CITADEL_BASE/citadel/.venv`
- Python 3.14
- Deps: anthropic, pyyaml, python-dotenv, pydantic, requests, openai, fastapi, uvicorn, jinja2

### Ollama Models Available
| Model | Type | Size | Notes |
|-------|------|------|-------|
| nemotron-3-nano:30b-cloud | REMOTE | 418B stub | Routes through ollama.com — NOT sovereign |
| qwen2.5-coder:14b-instruct-q5_K_M | LOCAL | 10.5GB | Fully local, sovereign ✅ |
| kimi-k2.5:cloud | REMOTE | 340B stub | Routes through ollama.com |
| minimax-m2.5:cloud | REMOTE | 337B stub | Routes through ollama.com |

**Sovereignty concern**: Default model `nemotron-3-nano` is cloud-routed. Must switch to `qwen2.5-coder:14b` for true local-first.

### Discord Bot
- Running as `Numenor_Prime_CEO#9279` in tmux session `athena-bot`
- Process: `python discord_bot_fixed.py` (pid confirmed alive)
- Commands: `!ulw`, `!athena`, `!stack`, `!sessions`, `!input`, `!log`, `!stop`, `!attach`, `!tail`

### LLM Config (`config/llm_models.yaml`)
- default_model: `local_llama`
- Fallback chain: anthropic_claude → local_llama → anthropic_haiku → openai_gpt4
- Only `local_llama` currently available (all cloud keys missing from CITADEL .env)

## Architecture: CITADEL Pipeline
```
User Input
  → WARDEN input validation (pattern-based threat detection)
  → Rate limiting (per user_id)
  → Task Router (keyword → ORACLE/PLUTUS/HERMES)
  → Agent execution (BaseAgent → LLM via adapter)
  → WARDEN output validation
  → Philosophical Triad (Bacon/Plato/Marcus, 2/3 consensus)
  → Audit Trail (Merkle tree)
  → Response
```

## Module Map (source files, excluding .venv)
```
orchestrator/
  citadel.py          — Main orchestrator (515 lines, full 7-step pipeline)
  task_router.py      — Keyword-based routing to agents
  consensus.py        — Re-export of validator consensus

modules/
  agents/
    base.py           — BaseAgent ABC with LLM integration
    registry.py       — Agent registry
    oracle/agent.py   — ORACLE (research/strategy)
    plutus/agent.py   — PLUTUS (finance/ledger)
    hermes/agent.py   — HERMES (communication)
  llm_adapters/
    interface.py      — LLMAdapter ABC
    loader.py         — ModelRegistry with fallback chain
    local_adapter.py  — Ollama integration
    anthropic_adapter.py
    openai_adapter.py
    google_adapter.py
  validators/
    interface.py      — Validator ABC
    consensus.py      — 2/3 majority consensus
    bacon/validator.py
    marcus/validator.py
    plato/validator.py
  warden/
    implementation.py — Pattern-based threat detection
    sanitizer.py      — Input sanitization
    patterns.py       — Threat patterns
    audit.py          — Security audit logging
    interface.py
  ledger/
    audit_trail.py    — Event logging
    merkle_tree.py    — Tamper-evident tree
    work_units.py     — JouleWork tracking
  knowledge_base/
    graph.py, loader.py, wikilink_parser.py
  containers/
    podman_orchestrator.py
  cache.py

citadel_server/
  main.py             — FastAPI app
  onboarding.py       — Agent onboarding flows
  storage.py          — JSON file storage
  voice.py            — Whisper ASR + voice routing
  templates/          — dashboard.html, agent.html, onboarding.html

guardian_server/
  main.py             — Separate server for Pi5 Warden node

mission_control/
  app.py, routes.py, models.py, io_ops.py

scripts/
  start_mission_control.py  — Port 9100
  smoke_test_mission_control.py

config/
  citadel.yaml        — Main config (warden, validation, triad policy)
  agents.yaml         — Agent config (ORACLE, PLUTUS, HERMES enabled)
  llm_models.yaml     — Model config with fallback chain
```

## Gap Analysis (CITADEL_v1 Spec vs CITADEL_BASE)

### Aligned ✅
- Agent architecture (ORACLE, PLUTUS, HERMES)
- WARDEN security gate
- Triad validation (2/3 consensus)
- Ollama local inference
- JouleWork/Ledger audit trail with Merkle tree
- FastAPI backend
- Config-driven architecture

### Missing ❌
- APOLLO agent (listed in spec, not built)
- CEO/Discord/ATHENA integration (standalone app)
- CORE memory integration (spec calls for RedPlanet Core)
- oh-my-opencode/ulw integration
- Avatar/Pepper's Ghost display driver
- NPU/iGPU hardware targeting
- Live dashboard (spec says Next.js, code has basic Jinja2)
- Naming: spec says Aurelius/Sun Tzu, code uses Marcus/Plato

## Integration Plan (Critical Path for Feb 19 Demo)

### Phase 1: Wire to Discord (Feb 17 — TODAY)
1. Start CITADEL FastAPI server as persistent tmux session
2. Add `!citadel <prompt>` command to Discord bot → POST to `/api/process`
3. Test end-to-end: Discord → Bot → CITADEL → Ollama → Response → Discord
4. Switch default model to `qwen2.5-coder:14b` for sovereignty

### Phase 2: Demo Hardening (Feb 18)
5. Add `!citadel-status` command showing system health
6. Test WARDEN blocking (prompt injection via Discord)
7. Test Triad Gate validation on decision-type queries
8. Co-start CITADEL server with Discord bot

### Phase 3: Demo Polish (Feb 18-19)
9. Boot ritual with Discord announcements
10. JouleWork logging visible in Discord
11. Clean up validator naming if desired

## Tailscale SSH Reference
| Device | SSH Command | Role |
|--------|------------|------|
| beelink | `ssh root@100.94.135.106` | Brain (target for CITADEL deployment) |
| raspberrypi | `ssh numenor@100.115.186.127` | Warden node |
| raspberrypi-1 | `ssh numenor2@100.78.248.81` | Avatar node |
| bluefin (local) | 100.127.2.59 | Forge (dev machine) |

## Key File Paths
- Blueprint: `/var/home/dward/Numenor_Prime/CITADEL_v1/`
- Codebase: `/var/home/dward/Eregion/CITADEL_BASE/citadel/`
- Discord bot: `/var/home/dward/Numenor_Prime/ATHENA/discord_bot_fixed.py`
- Bot start script: `/var/home/dward/Numenor_Prime/ATHENA/scripts/start_discord_bot.sh`
- CITADEL venv: `/var/home/dward/Eregion/CITADEL_BASE/citadel/.venv`
- CITADEL config: `/var/home/dward/Eregion/CITADEL_BASE/citadel/config/`
- Ollama: `http://localhost:11434`

## Constraints (Verbatim)
- "I am in a time crunch to get Citadel to a stable condition"
- "long term I do not want the messaging system reliant on quota usage from another company"
- "be careful with token usage and switch accordingly"
- Platform: BluefinOS (Fedora atomic/immutable)
- Output to Eregion
