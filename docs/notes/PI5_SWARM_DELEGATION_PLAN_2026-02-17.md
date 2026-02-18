# Pi5 Swarm Delegation Plan (Queued for Later Implementation)

Date: 2026-02-17
Owner: ARANDUR
Status: queued_for_batch_6

## Intent

Extend ATHENA from single-host + cloud fallback into mesh-aware delegation across Tailscale devices (Pi5 nodes), while preserving SOUL.md governance and local-first operation.

## Confirmed Existing Signals (From Repository Search)

- Tailscale mesh manifest already exists: `CITADEL_v1/REMOTE/MESH_MANIFEST.yaml`
- Pi5 scout hostnames already tracked: `raspberrypi`, `raspberrypi-1` in `Tools/pulse_check.sh`
- Existing ATHENA fleet abstraction exists: `athena/fleet/node_registry.py`
- Existing ATHENA queue + armoury node exists: `athena/interfaces/arandur_node.py`
- Company task schema exists: `Operations/Tasks/task_schema.yaml`
- JouleWork supports Pi5 device attribution: `Operations/Ledger/joulework/jw_entry_schema.yaml`

## Proposed Batch 6 Scope

1. Add mesh discovery adapter for ATHENA
   - Source of truth priority:
     1) `CITADEL_v1/REMOTE/MESH_MANIFEST.yaml`
     2) `tailscale status --json`
   - Output: normalized `ComputeNode` records with role, host, status, and capabilities.

2. Add delegation policy for Pi5 scouts
   - Delegate scout/research/integration tasks to Pi5 when reachable and healthy.
   - Keep local host first for sensitive tasks.
   - Keep cloud providers as fallback only when local mesh is insufficient.

3. Add per-node governance files
   - `ATHENA/athena/fleet/node_profiles/<node>.soul.yaml`
   - `ATHENA/athena/fleet/node_profiles/<node>.capabilities.yaml`

4. Add execution/audit logging for assessments
   - Persist each delegated event with:
     - node id, task id, mission id, timing, outcome, model/provider, energy estimate
   - Store in machine-readable log and summarize into periodic assessment report.

## Communication Policy (Executive Channels)

- Primary relay: Discord CEO channel via ATHENA interface
- Durable machine log: ATHENA garrison under `armoury/`
- Governance queue alignment: mirror major delegation outcomes to `Operations/Tasks/queue.yaml` and `Operations/Ledger/joulework/jw_log.yaml`

## Deferred Implementation Gate

Implementation is intentionally deferred to next batch.
This document is the queued execution contract for that batch.
