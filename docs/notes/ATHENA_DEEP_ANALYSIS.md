# ATHENA Deep Codebase Analysis

**Date**: 2026-02-17
**Analyst**: Arandur (Claude Code / Sisyphus)
**Purpose**: Full assessment of every ATHENA source file — what's real, what's stubbed, what's missing, and where to expand. This document is the single source of truth for any future agent continuing ATHENA expansion work.

---

## 1. Codebase Summary

| File | Lines | Status | Assessment |
|------|-------|--------|------------|
| `athena.py` | 1724 | **REAL** | Production-quality orchestrator. Core memory integration, battle planning, mission lifecycle all functional. |
| `apollo.py` | 488 | **PARTIAL** | Structure solid. 6 Titans defined. Only ORPHEUS has real GitHub scouting (via `GitHubScout`). HELIOS has hardcoded repo lists. Others are shells. |
| `ares.py` | 500 | **PARTIAL** | Same pattern as APOLLO. 6 Titans defined. HYPERION has `scout_api_repos()` with hardcoded data. PROMETHEUS has `scout_database_patterns()` returning static list. Others are shells. |
| `artemis.py` | 510 | **SIMULATED** | Testing campaign is entirely simulated — hardcoded test counts (47/50 passed, 87% coverage). No real test execution. Framework is correct but all data is fake. |
| `hermes.py` | 112 | **MINIMAL** | 3 Titans (IRIS, HERMES_BUS, COURIER). Bare deploy/routing. No actual communication logic. |
| `hephaestus.py` | 256 | **REAL** | Actually runs subprocess commands. `run_stage()` executes real shell commands with timeout. `_build_stage_commands()` generates real podman/python/tmux commands. This is the most "real" Olympian after ATHENA core. |
| `github_scout.py` | 1023 | **REAL** | Full GitHub API client (REST, rate limiting, retry, caching). Real repo search, tree fetching, dependency extraction, quality scoring. Fallback simulation when API unavailable. Production-quality code. |
| `code_integrator.py` | 625 | **SIMULATED** | Framework is correct (7-step integration pipeline). But all steps are placeholder logic — conflict resolution counts but doesn't resolve, interface generation creates template strings, implementation combining just concatenates comments. |
| `discord_bot_fixed.py` | 774 | **REAL** | Full Discord bot with tmux-based OpenCode session management. Real subprocess execution, log streaming, session monitoring. `!ulw`, `!athena`, `!citadel`, `!citadel-status` commands. Production-ready. |
| `citadel_pod_coordinator.py` | 431 | **REAL** | Real Podman pod lifecycle management. `podman pod start/stop/ps` commands. Priority queue, idle timeout, max concurrent pods. `_execute_task()` is simulated (sleep) but framework is real. |
| `ceo_athena_bridge.py` | 15 | **MINIMAL** | Thin wrapper. Just instantiates ATHENA + AthenaCommander and calls `issue_objective()`. |
| `models.py` | 89 | **NOTES** | Not real code — it's a markdown-formatted analysis document about model costs and open source strategy. Contains a Python dict of model assignments but inside a markdown code fence with a stray closing backtick on line 39. Won't parse as Python. |
| `distributed.py` | 29 | **STUB** | Just a dict of 2 compute nodes and a `assign_agent_to_node()` function referencing undefined `HEAVY_TITANS`, `SCOUTS`, and `get_current_load()`. Non-functional. |
| `model_manager.py` | 31 | **STUB** | Hardcoded URL routing for agent types. References models that don't exist yet (`qwen3.5:*`). No actual model loading or inference. |
| `olympians/base.py` | 18 | **STUB** | Just `AVAILABLE_MODELS` dict and a 3-line `Titan` class. Not used by any Olympian (they all define their own `Titan` class). |

**Total**: ~6,635 lines across 15 Python files.

---

## 2. Architecture Assessment

### What Works Well

1. **Military hierarchy is consistent** — ATHENA → Olympian → Titan → Hero → Warrior → Hoplite. Every file follows this.

2. **Mission lifecycle is complete** — `receive_objective()` → `_analyze_objective()` → `_decompose_objective()` → `_create_battle_plan()` → `_deploy_olympians()` → `complete_mission()`. All states tracked.

3. **Core memory integration is deep** — `CoreMemoryClient` (cloud) and `LocalCoreMemoryClient` (SQLite) with episode storage, knowledge graph search, ingestion refresh polling. Events persisted at every lifecycle stage.

4. **GitHub Scout is production-grade** — Real API client with auth, rate limiting, caching (TTL-based), retry on 429/403, tree walking, dependency extraction from requirements.txt/setup.py/pyproject.toml, quality scoring algorithm.

5. **Discord bot is functional** — Real tmux session management, log streaming to Discord, `!citadel` command routes through CITADEL HTTP API, session monitoring background task.

6. **Pod coordinator handles real Podman** — `podman pod start/stop/ps` with async lifecycle, priority queue, idle timeout, max concurrent pod enforcement.

7. **CLI interface is well-designed** — `argparse` with Core configuration, auto-register toggle, status mode. Environment variable fallbacks throughout.

### Critical Gaps

1. **NO LLM INTEGRATION** — The biggest gap. `_decompose_objective()` uses keyword matching (`has_any(["voice", "audio"])`) to generate components. The TODO on line 1134 says "Use LLM to intelligently decompose based on objective description." No agent actually calls an LLM to reason about anything. The entire intelligence layer is heuristic.

2. **NO ACTUAL CODE EXECUTION** — Scouts find repos, but no agent actually clones, reads, or modifies code. `code_integrator.py` generates placeholder strings. There's no AST parsing, no code extraction, no real synthesis.

3. **NO INTER-AGENT COMMUNICATION** — Olympians don't talk to each other. ATHENA deploys them but they operate in isolation. No message bus, no shared state beyond ATHENA's `intel_stream`. No event system.

4. **DUPLICATED Titan/TitanReport CLASSES** — Every Olympian file (`apollo.py`, `ares.py`, `artemis.py`, `hermes.py`, `hephaestus.py`) defines its own `Titan` and `TitanReport` classes. These are near-identical. Should be in a shared base module. `olympians/base.py` exists but nobody uses it.

5. **FLAT MODULE LAYOUT** — All files at top level with `sys.path.append(str(Path(__file__).parent.parent))`. No proper Python package structure. Imports will break if files move.

6. **HARDCODED FALLBACK DATA** — When GitHub API is unavailable, scouts return hardcoded Picovoice/Whisper/Coqui repos. The user explicitly rejected hardcoded fallbacks in CITADEL — same principle should apply here.

7. **NO ASYNC IN CORE** — `athena.py` is entirely synchronous. `citadel_pod_coordinator.py` is async but doesn't integrate with ATHENA. For parallel Olympian deployment, async is essential.

8. **BROKEN SUPPORT FILES**:
   - `models.py` — Markdown, not Python. Will crash on import.
   - `distributed.py` — References undefined symbols (`HEAVY_TITANS`, `SCOUTS`, `get_current_load`).
   - `model_manager.py` — Hardcoded URLs to non-existent models.
   - `olympians/base.py` — Unused by anything.

9. **NO TESTS** — Zero test files. No pytest fixtures, no CI configuration. ARTEMIS simulates testing but doesn't test ATHENA itself.

10. **NO ERROR RECOVERY** — If an Olympian fails deployment, ATHENA logs a warning and continues. No retry, no fallback routing (except the hardcoded `_resolve_olympian_fallback` for HERMES→ARES→APOLLO), no circuit breaker.

---

## 3. File-by-File Deep Analysis

### athena.py (1724 lines) — The Crown Jewel

**Classes:**
- `Priority(Enum)` — 5 levels: ROUTINE through EMERGENCY
- `MissionStatus(Enum)` — 9 states: RECEIVED through ABORTED
- `DivisionStatus(Enum)` — 5 states: STANDBY through OFFLINE
- `Objective` — Dataclass with description, deadline, priority, constraints, success_criteria
- `Component` — Dataclass with name, type, priority, dependencies, assigned_to, status, progress
- `BattlePlan` — Dataclass linking Objective → Components → Olympians
- `Intel` — Dataclass for field reports (source, timestamp, message, severity, data)
- `MissionReport` — Dataclass for mission completion reporting
- `CoreMemoryClient` — HTTP client for RedPlanet Core cloud API
- `LocalCoreMemoryClient` — SQLite-based local memory (WAL mode, schema auto-init)
- `Olympian` — Base class for division commanders
- `ATHENA` — Supreme commander class (the main orchestrator)
- `AthenaCommander` — Human interface wrapper

**Core Memory Integration (lines 181-996):**
The most sophisticated part. `_persist_core_event()` records every lifecycle event. `_retrieve_core_context()` searches knowledge graph before planning. `_apply_core_priority_weighting()` adjusts component priorities based on Core context using keyword matching against component types. `_extract_component_templates()` pulls reusable templates from Core search results. `_merge_component_templates()` adds relevant templates to planning. `refresh_core_ingestion()` polls for pending events to become searchable. This is ~800 lines of real, working Core integration.

**Objective Decomposition (lines 1099-1202):**
THIS IS THE KEY BOTTLENECK. `_decompose_objective()` does keyword matching on the objective description + Core context text. If description contains "voice" or "audio", it adds audio components. If it contains "api" or "backend", it adds API components. This is where an LLM should be doing the decomposition. The heuristic works for demos but can't handle novel objectives.

**Olympian Deployment (lines 1277-1387):**
Iterates `olympians_required` from the battle plan, checks if each is registered, assigns components to matching Olympians via `_component_matches_domain()` (keyword→domain mapping). Fallback routing only covers HERMES→ARES→APOLLO and HEPHAESTUS→ARES→APOLLO. Deploy is synchronous and sequential.

**CLI (lines 1600-1724):**
Full argparse with --objective, --deadline, --priority, --garrison-path, --core-mode, --core-base-url, --core-api-key, --core-score-threshold, --core-template-score-threshold, --core-refresh-timeout, --core-refresh-before-plan, --require-core, --status, --no-auto-register. Well-designed for programmatic invocation from Discord bot.

### apollo.py (488 lines) — Frontend & Creative

**Titans:** HELIOS (UI), SELENE (theming), MNEMOSYNE (state mgmt), CALLIOPE (content), TERPSICHORE (animation), ORPHEUS (voice/audio)

**Real functionality:** Only `ORPHEUS.scout_voice_repos()` does real work — calls `GitHubScout.scout_repositories()` then `analyze_components()`. `HELIOS.scout_repositories()` returns hardcoded repo list. `HELIOS.extract_components()` returns template dicts. All others have no scouting methods.

**Routing:** `_select_titan()` uses keyword matching on component name. Voice→ORPHEUS, UI→HELIOS, theme→SELENE, state→MNEMOSYNE, animation→TERPSICHORE, content→CALLIOPE. Default→HELIOS.

### ares.py (500 lines) — Backend Warfare

**Titans:** PROMETHEUS (DB/ORM), ATLAS (workers), HYPERION (API routing), OCEANUS (streaming), CRONOS (scheduling), HADES (auth/security)

**Real functionality:** `HYPERION.scout_api_repos()` returns hardcoded list with scores. `PROMETHEUS.scout_database_patterns()` returns hardcoded repo list. Others have no methods beyond inherited deploy.

**Same pattern as APOLLO** — keyword routing, sequential deployment, progress tracking.

### artemis.py (510 lines) — Testing & QA

**Titans:** ORION (E2E), ACTAEON (performance), CALLISTO (security), ATALANTA (speed), MELEAGER (coverage)

**Key issue:** `_execute_testing_campaign()` runs all 5 phases but every metric is hardcoded: `unit_tests_passed = 47`, `coverage = 0.87`, `vulnerabilities = 2`, `benchmark_tests = 10`, etc. No actual test execution happens. Quality assessment at end uses these fake numbers.

**CALLISTO.scout_security_tools()** returns hardcoded results. Only method with any logic beyond base class.

### hermes.py (112 lines) — Communications

**Titans:** IRIS (webhooks/events), HERMES_BUS (API routing), COURIER (session/message transport)

**Minimal implementation.** Deploy selects titan by keyword, updates progress to 0.4, increments relay counter. No actual communication logic, no webhook handling, no message transport.

### hephaestus.py (256 lines) — Infrastructure & Forge

**Titans:** FORGE_MASTER (build/compile), ANVIL (container/image), EMBER (deployment/hardening)

**ACTUALLY RUNS COMMANDS.** `Titan.run_stage()` uses `subprocess.run()` with capture, timeout, exit code checking. `_execute_pipeline()` chains stage commands and fails fast on non-zero exit. `_build_stage_commands()` generates real commands:
- FORGE_MASTER: `python -m compileall`, `python athena.py --status`
- ANVIL: `podman --version`, `podman pod ps`
- EMBER: `opencode --version`, `zeptoclaw status`
- Deployment components get `scripts/preflight_check.sh`

This is the only Olympian that does real work beyond scouting.

### github_scout.py (1023 lines) — The Best Module

**Classes:** `GitHubAPIClient`, `Repository`, `ComponentFindings`, `ScoutReport`, `GitHubScout`, `ACHILLES`, `ODYSSEUS`, `PERSEUS`

**GitHubAPIClient:** Full REST client using stdlib urllib. Token-based auth via GITHUB_TOKEN env. Rate limit tracking (both standard and search). Retry on 429/403 with backoff. 15s timeout.

**GitHubScout:** 
- `scout_repositories()` → `_search_github()` (real API) → `_parse_repository()` → `_detect_quality_signals()` (fetches tree, checks for tests/docs/CI) → `_qualify_repository()` (license check, activity check, quality score)
- `analyze_components()` → `_get_file_tree()` → `_match_components_to_files()` (keyword scoring against file paths) → `_extract_dependencies()` (parses requirements.txt, setup.py, pyproject.toml)
- Caching layer with TTL: search results (1h), trees (24h), deps (24h), file content (24h)
- Quality score: stars(0.3) + tests(0.2) + docs(0.2) + CI(0.1) + low issues(0.1) + recent activity(0.1)

**Specialized heroes (ACHILLES, ODYSSEUS, PERSEUS)** are just named subclasses with different specialties. No behavior differences.

### code_integrator.py (625 lines) — Framework Only

**7-step pipeline:**
1. `_resolve_naming_conflicts()` — Counts conflicts but doesn't resolve them
2. `_merge_dependencies()` — Real: deduplicates and sorts
3. `_generate_interface()` — Generates template class string
4. `_combine_implementations()` — Concatenates source attribution comments
5. `_generate_glue_code()` — Generates template integrator class string
6. `_generate_tests()` — Generates template pytest class string
7. `_generate_documentation()` — Generates template markdown string

Only step 2 does real work. Everything else produces placeholder code. This needs LLM integration to generate real code.

### discord_bot_fixed.py (774 lines) — Production-Ready

**Commands:** `!ulw <task>`, `!input <session> <text>`, `!log <session> [lines]`, `!attach <session>`, `!stop <session>`, `!sessions`, `!stack`, `!citadel <prompt>`, `!citadel-status`, `!athena <objective>`, `!tail <filepath> [lines]`

**OpenCodeSession class:** Creates tmux sessions, writes prompt files, manages log files, sends input via `tmux send-keys`, reads new output lines, checks session liveness.

**Autonomous mode:** When `channel_autonomy[channel_id]` is True, freeform messages route to running session. When session completes, `channel_awaiting_next_task` enables reply-to-continue flow with recommended next task.

**CITADEL integration:** `!citadel` POSTs to `CITADEL_URL/api/process` with prompt/context/user_id. Displays agents used, validation status, triad review requirement.

**Stack validation:** Checks for tmux, opencode, zeptoclaw, picoclaw, oh-my-opencode config, CORE_API_KEY.

### citadel_pod_coordinator.py (431 lines) — Real Infrastructure

**PodManager:** Maps agent names to pod names. Tracks pod states. `start_pod()` calls `podman pod start`. `stop_pod()` calls `podman pod stop`. `stop_idle_pods()` checks last-used timestamps against 5-minute timeout.

**CitadelPodCoordinator:** Async priority queue. `submit_request()` queues with priority. `_process_queue()` dequeues, checks running pod count against `max_concurrent_pods`, stops oldest idle pod if at capacity, starts needed pod. `_execute_task()` is placeholder (just sleep).

**Key constraint:** `max_concurrent_pods=2` — designed for Beelink SER9 with 8GB shared VRAM.

---

## 4. Dependency Map

### Internal Dependencies
```
athena.py          → (standalone, no internal imports)
apollo.py          → athena.py (Olympian, Component, Intel, DivisionStatus)
                   → github_scout.py (GitHubScout)
ares.py            → athena.py
artemis.py         → athena.py
hermes.py          → athena.py
hephaestus.py      → athena.py
github_scout.py    → (standalone)
code_integrator.py → (standalone)
discord_bot_fixed.py → athena.py (ATHENA, AthenaCommander)
citadel_pod_coordinator.py → (standalone, uses podman CLI)
ceo_athena_bridge.py → athena.py (ATHENA, AthenaCommander)
```

### External Dependencies (from code analysis)
```
stdlib only:      athena.py, github_scout.py, code_integrator.py, 
                  citadel_pod_coordinator.py, hephaestus.py
discord.py:       discord_bot_fixed.py (discord, discord.ext.commands/tasks)
aiohttp:          discord_bot_fixed.py (HTTP client for CITADEL)
dotenv:           discord_bot_fixed.py (optional)
```

### Runtime Dependencies (from docs + code)
```
Podman:           citadel_pod_coordinator.py, hephaestus.py
tmux:             discord_bot_fixed.py, hephaestus.py
opencode:         discord_bot_fixed.py, hephaestus.py
zeptoclaw:        discord_bot_fixed.py, hephaestus.py
picoclaw:         discord_bot_fixed.py
Ollama:           (referenced in distributed.py/model_manager.py but not actually used)
RedPlanet Core:   athena.py (cloud or local SQLite)
GitHub API:       github_scout.py (optional, has fallback)
```

---

## 5. Model Assignment Plan (from models.py)

This was a planning document, not executable code. The intended model assignments:

| Tier | Agent | Model | Cost |
|------|-------|-------|------|
| Supreme | ATHENA | claude-opus-4-6 | ~$20 |
| Olympian | APOLLO, ARES, ARTEMIS | claude-sonnet-4-6 | ~$30 total |
| Titan (heavy) | PROMETHEUS, ATLAS, HYPERION, HADES, CALLISTO | qwen3.5-72b | $0 |
| Titan (medium) | OCEANUS, CRONOS, HELIOS, SELENE, MNEMOSYNE, CALLIOPE, ORPHEUS, ORION, ACTAEON, ATALANTA, MELEAGER | qwen3.5-14b | $0 |
| Titan (light) | TERPSICHORE | qwen3.5-7b | $0 |
| Hero | ACHILLES, ODYSSEUS, PERSEUS | qwen3.5-7b | $0 |
| Warrior | HEPHAESTUS | qwen3.5-14b | $0 |

**Estimated total: ~$50 per major mission** (vs $200+ all-cloud)

The compute distribution plan (from distributed.py):
- **Primary** (localhost:11434, RTX 3080, 10GB): qwen3.5:14b-q4, qwen3.5:7b-fp16
- **Scout** (beelink:11435, Radeon 780M, 8GB): qwen3.5:7b-q4, qwen3.5:3b-fp16

---

## 6. What Exists but Isn't Connected

| Component | Exists In | Connected To | Gap |
|-----------|-----------|--------------|-----|
| Core Memory | athena.py | Battle planning, event persistence | Not used by any Olympian directly |
| GitHub Scout | github_scout.py | ORPHEUS (apollo.py) | Not used by ARES or other Olympians' scouting |
| Code Integrator | code_integrator.py | Nothing | Never called from any Olympian or ATHENA |
| Pod Coordinator | citadel_pod_coordinator.py | Nothing | Not integrated with ATHENA deployment |
| Discord Bot | discord_bot_fixed.py | ATHENA CLI, CITADEL HTTP API | Works but sessions are isolated |
| Hephaestus Pipeline | hephaestus.py | ATHENA deployment | Only Olympian that runs real commands |
| Model Manager | model_manager.py | Nothing | Dead code |
| Distributed Config | distributed.py | Nothing | Dead code |

---

## 7. Expansion Priority Matrix

### P0: Make It Actually Think (LLM Integration)
The single biggest upgrade. Replace keyword-based `_decompose_objective()` with LLM-powered task decomposition. Wire LLM calls into Olympian decision-making. This transforms ATHENA from a demo framework into a real AI system.

### P1: Make Agents Talk to Each Other (Message Bus)
Inter-agent communication. Event-driven architecture. Shared state. Currently each Olympian is an island. Need a message bus (could be simple: Redis pubsub, SQLite WAL, or in-process asyncio queues).

### P2: Make Code Integration Real (AST + LLM)
Replace placeholder `code_integrator.py` with real code synthesis. Use AST parsing for extraction, LLM for glue code generation, real dependency resolution.

### P3: Package Structure & Shared Base
- Move to proper Python package (`athena/`)
- Single shared `Titan` and `TitanReport` base class
- Remove duplicated code across Olympian files
- Fix `models.py`, `distributed.py`, `model_manager.py`

### P4: Async Core
Make `athena.py` async. Parallel Olympian deployment. Non-blocking scouting. This enables real concurrent operations.

### P5: Container Orchestration
Connect `citadel_pod_coordinator.py` to ATHENA deployment. Olympians spin up as pods on demand. GPU-aware scheduling.

### P6: Test Suite
ATHENA has zero tests. Build a real test suite. Make ARTEMIS test ATHENA itself (meta-testing).

---

## 8. Architectural Patterns to Preserve

These decisions are intentional and should not be changed:

1. **Military hierarchy naming** — This is the user's vision. Every agent maps to a rank.
2. **Sovereignty-first** — Local LLMs preferred. Cloud only for strategic decisions.
3. **Core Memory integration** — RedPlanet Core for persistent memory. Keep both local and cloud modes.
4. **Podman over Docker** — BluefinOS native. Immutable OS constraints.
5. **Discord as CEO interface** — Bot commands are the primary control channel.
6. **OpenCode + oh-my-opencode** — Autonomous code execution via tmux sessions.
7. **Dynamic discovery** — User explicitly rejected hardcoded fallbacks. System should discover what's available.
8. **Resource-aware** — Everything must work on RTX 3080 (10GB) + Beelink SER9 (8GB shared).

---

## 9. Runtime State (as of 2026-02-17)

- **Ollama running** with `qwen2.5-coder:7b` (4.7GB, GPU) on primary node
- **CITADEL server** operational at `localhost:8000`
- **No GITHUB_TOKEN set** — Scout will use fallback data
- **No DISCORD_BOT_TOKEN set** — Bot not running
- **No CORE_API_KEY set** — Cloud Core unavailable, local SQLite mode works
- **Garrison path**: `~/Eregion/athena-garrison/`
- **No scripts/ or build_files/ directories exist** — referenced in docs but not created

---

## 10. Key Code Locations for Expansion

| What You're Changing | File | Line | Function/Class |
|---------------------|------|------|----------------|
| Task decomposition | athena.py | 1125 | `_decompose_objective()` |
| Component-to-Olympian routing | athena.py | 1243 | `_determine_olympians()` |
| Olympian deployment | athena.py | 1277 | `_deploy_olympians()` |
| Fallback routing | athena.py | 1350 | `_resolve_olympian_fallback()` |
| Olympian registration | athena.py | 1397 | `register_default_olympians()` |
| Core memory search | athena.py | 670 | `_retrieve_core_context()` |
| Core memory persist | athena.py | 640 | `_persist_core_event()` |
| Titan base class | apollo.py | 49 | `class Titan` (duplicated everywhere) |
| GitHub API client | github_scout.py | 33 | `class GitHubAPIClient` |
| Repository scoring | github_scout.py | 605 | `_calculate_quality_score()` |
| Component matching | github_scout.py | 738 | `_match_components_to_files()` |
| Pod lifecycle | citadel_pod_coordinator.py | 51 | `class PodManager` |
| Discord session | discord_bot_fixed.py | 144 | `class OpenCodeSession` |
| CLI entry point | athena.py | 1600 | `if __name__ == "__main__"` |

---

## 11. The Fleet Vision — Distributed ATHENA Over Tailscale

**THIS IS THE ENDGAME.** ATHENA isn't a single-machine process. She's a **fleet commander** operating across a Tailscale mesh network:

### Hardware Fleet (Current)
| Node | Hardware | GPU | VRAM | Role | Tailscale Access |
|------|----------|-----|------|------|-----------------|
| **Primary** | Main PC | RTX 3080 | 10GB | Heavy inference (14b+ models), ATHENA Supreme Commander | localhost |
| **Beelink** | Beelink SER9 | Radeon 780M | 8GB shared | Medium inference (7b models), persistent services | SSH via Tailscale |
| **Pi5 Fleet** | Raspberry Pi 5 | None (CPU) | 8GB RAM | Scouts, monitoring, lightweight agents, persistent watchers | SSH via Tailscale |

### The Vision
When ATHENA is at "optimum efficiency", she:

1. **Discovers the fleet** — Queries Tailscale for available nodes, probes each for resources (GPU type, VRAM available, CPU cores, RAM, running services)
2. **Deploys agents where they fit** — Heavy Titans (PROMETHEUS, ATLAS, HADES) on RTX 3080. Medium Titans (HELIOS, SELENE, ORION) on Beelink. Scouts and monitors on Pi5s.
3. **SSH installs what she needs** — If a Pi5 doesn't have Ollama, ATHENA SSHs in, installs it, pulls the right model, starts the service. Self-provisioning.
4. **Routes tasks dynamically** — When Primary's GPU is busy with a 14b model, queue lighter work to Beelink. When all GPUs are saturated, queue to CPU-only Pi5 nodes with 3b models for non-critical work.
5. **Manages the whole fleet as one brain** — Single ATHENA instance on Primary coordinates everything. Olympians can physically span multiple machines. APOLLO's ORPHEUS might run on Primary (voice needs GPU), while APOLLO's CALLIOPE runs on Pi5 (text generation is lightweight).

### Key Infrastructure Patterns Needed
- **Node Discovery**: Tailscale API or `tailscale status --json` to enumerate nodes
- **Resource Probing**: SSH + `nvidia-smi` / `rocm-smi` / `/proc/meminfo` to assess capacity
- **Remote Deployment**: SSH + `podman` to start/stop containers on remote nodes
- **Service Mesh**: Each node runs an agent endpoint (HTTP/gRPC). ATHENA routes to the right node.
- **Health Monitoring**: Heartbeat from each node. Auto-failover if a Pi5 goes offline.
- **Model Placement**: `distributed.py` concept but actually functional — which model on which node, dynamically decided.

### Container Topology (Per Node)
```
Primary Node (RTX 3080):
  Pod: athena-command
    Container: athena-core (Supreme Commander)
    Container: ollama (qwen2.5-coder:7b or :14b)
  Pod: ares-cluster
    Container: ares-olympian
    Container: prometheus-titan
    Container: hyperion-titan

Beelink Node (Radeon 780M):
  Pod: apollo-cluster
    Container: apollo-olympian
    Container: helios-titan
    Container: ollama (qwen:7b-q4)

Pi5 Nodes (CPU only):
  Pod: scout-cluster
    Container: achilles-hero (GitHub scout)
    Container: odysseus-hero (integration scout)
    Container: ollama (qwen:3b)
  Pod: monitor-cluster
    Container: health-watcher
    Container: discord-relay
```

---

## 12. External Framework Analysis (Research Summary)

### Framework Comparison Matrix

| Framework | Architecture | Communication | Task Decomposition | Memory | Best For | Steal For ATHENA |
|-----------|-------------|---------------|-------------------|--------|----------|-----------------|
| **CrewAI** | Role-based agent teams | Sequential/parallel task pipelines | Declarative task definitions with expected outputs | Short-term (conversation), long-term (optional) | Quick prototyping, role-based workflows | Role definition pattern, task delegation with expected output format |
| **AutoGen** | Event-driven async multi-agent conversations | Agent-to-agent messaging, group chat | Conversation-driven decomposition | Conversation history per agent | Complex multi-turn reasoning, research | Event-driven architecture, async agent messaging |
| **LangGraph** | Graph-based state machines with explicit control flow | State object passed between nodes | Graph nodes = steps, edges = conditions | Checkpointed state at every node | Production systems needing auditability, human-in-loop | **State checkpointing, graph-based control flow, human-in-loop interrupts** |
| **OpenAI Swarm** | Lightweight handoff-based | Function-call handoffs between agents | Triage agent routes to specialists | Context variables dict | Simple routing, customer service | Handoff pattern simplicity, context_variables dict |
| **MetaGPT** | Software company simulation (PM→Architect→Engineer→QA) | Structured output documents (PRD, design, code) | SOPs (Standard Operating Procedures) | Shared workspace/blackboard | Code generation pipelines | SOP concept for standardizing Olympian outputs |
| **SWE-Agent** | Single autonomous coding agent | Tool calls (file edit, terminal, search) | Agent decomposes internally via chain-of-thought | Conversation + file state | Autonomous code changes | Tool interface design for Hephaestus-style code execution |

### Key Patterns to Adopt

#### 1. From LangGraph: State Checkpointing
**Why**: ATHENA currently has no way to resume a failed mission. If the process dies mid-deployment, all state is lost. LangGraph checkpoints state at every graph node.
**How**: Add `mission_state.json` persistence at every lifecycle transition. When ATHENA restarts, it can resume from last checkpoint.

#### 2. From AutoGen: Event-Driven Messaging
**Why**: ATHENA's Olympians can't talk to each other. AutoGen's agent-to-agent messaging enables emergent collaboration.
**How**: Add an async message bus (could be as simple as SQLite WAL table or Redis pubsub). Olympians publish intel, subscribe to relevant topics.

#### 3. From CrewAI: Expected Output Contracts
**Why**: When ATHENA deploys an Olympian, there's no contract for what the Olympian should return. CrewAI tasks have `expected_output` fields.
**How**: Components should define success criteria and output schema. ATHENA validates outputs against contracts.

#### 4. From MetaGPT: SOPs (Standard Operating Procedures)
**Why**: Each Olympian invents its own workflow. MetaGPT standardizes outputs (PRD → Design → Code → Tests).
**How**: Define SOPs for each mission type. "Code harvesting" SOP: Scout → License Check → Quality Score → Extract → Integrate → Test → Deploy.

#### 5. From A2A Protocol: Agent Cards for Discovery
**Why**: ATHENA currently hardcodes which Olympians exist. A2A protocol defines "Agent Cards" — JSON metadata at `/.well-known/agent.json` describing capabilities.
**How**: Each Olympian/Titan publishes an agent card. ATHENA discovers available agents dynamically. This is exactly what the user meant by "make it dynamic, nothing hardcoded."

#### 6. From MCP: Standardized Tool Interface
**Why**: Different agents access tools differently. MCP provides a standard way for agents to discover and use tools.
**How**: ATHENA's tool access (GitHub API, Podman, SSH, file system) should go through a standardized MCP-like interface that any agent can use.

### What NOT to Adopt

- **CrewAI's simplicity** — Too simple for ATHENA's military hierarchy. No graph control flow.
- **AutoGen's conversation-first model** — ATHENA is task-first, not chat-first. Agents should execute, not converse.
- **OpenAI Swarm's single-threaded handoffs** — ATHENA needs parallel deployment, not sequential handoffs.
- **MetaGPT's rigid role chain** — ATHENA's Olympians operate in parallel domains, not a linear PM→Dev→QA pipeline.

---

## 13. Container & GPU Deployment Patterns (Research Summary)

### Podman AI Lab (Red Hat)
- **Podman Desktop 1.12+** has native GPU acceleration for AI workloads
- CDI (Container Device Interface) for GPU passthrough
- `--device nvidia.com/gpu=all` flag for container GPU access
- Relevant: BluefinOS is Fedora-based, Podman-native. This is the correct path.

### vLLM Distributed Inference
- **Multi-node inference** over TCP using tensor parallelism + pipeline parallelism
- Fedora + Podman setup documented (matches our stack exactly)
- For ATHENA: Could serve a single large model across Primary + Beelink nodes
- **Edge deployment** (Jetson Orin Nano, 8GB): vLLM vs llama.cpp comparison shows llama.cpp better for <8GB devices, vLLM better for throughput-optimized serving
- Ollama is simpler for our use case (single-model serving per node)

### GPU Sharing Strategies
| Strategy | How It Works | Good For ATHENA? |
|----------|-------------|-----------------|
| **Time-slicing** | NVIDIA MPS shares GPU across processes | Yes — multiple small models on RTX 3080 |
| **vLLM batching** | Single vLLM instance handles concurrent requests | Yes — if we switch from Ollama to vLLM |
| **Ollama concurrent** | Ollama 0.3+ supports concurrent model loading | Yes — simplest path, already running |
| **Pod scheduling** | Only one GPU-heavy pod at a time, queue others | Yes — `citadel_pod_coordinator.py` already does this |

### Recommended Path for ATHENA
1. **Keep Ollama** for now — it works, it's simple, it handles model management
2. **Podman pods per Olympian cluster** — each Colonel is a pod with Titan containers
3. **GPU pod mutex on constrained nodes** — only one GPU-heavy pod per node (already in pod coordinator)
4. **SSH + Podman for remote deployment** — ATHENA SSHs to Beelink/Pi5, runs `podman pod create/start`
5. **Evaluate vLLM** when serving multiple concurrent requests becomes a bottleneck
6. **Tailscale as the network fabric** — all inter-node communication over Tailscale IPs (encrypted, zero-config)

---

## 14. Decision Log

| Decision | Rationale | Date |
|----------|-----------|------|
| Military hierarchy naming | User's founding vision. Non-negotiable. | Pre-existing |
| Sovereignty-first (local LLMs) | User principle in SOUL.md | Pre-existing |
| Podman over Docker | BluefinOS native, immutable OS | Pre-existing |
| Dynamic discovery over hardcoded | User explicitly rejected hardcoded fallbacks | 2026-02-16 |
| Keep Ollama (don't switch to vLLM yet) | Works now, switching adds complexity for no current benefit | 2026-02-17 |
| A2A-style Agent Cards for discovery | Matches "dynamic, nothing hardcoded" requirement | 2026-02-17 |
| LangGraph-style state checkpointing | Critical for mission resumability | 2026-02-17 |
| Event-driven message bus for Olympians | Enables inter-agent communication without coupling | 2026-02-17 |
| Fleet deployment over Tailscale SSH | Matches existing infrastructure, user confirmed Pi5/Beelink access | 2026-02-17 |

---

*This document is the canonical reference for ATHENA expansion. Any future agent should read this FIRST before modifying ATHENA code.*
