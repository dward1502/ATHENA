# Project Context + Install Rewrite Note

Date: 2026-02-16

## User Context

- Current work is on laptop.
- `Numenor Prime` exists on the main PC as the company folder.
- The autonomous CEO interacts via Discord on the main PC.
- Current integration issue: Discord connection path is not fully working yet.

## Intended System Flow

1. ATHENA runs inside `Numenor Prime`.
2. Once stable, ATHENA builds out CITADEL workflows/components.
3. AI CEO can drive overnight progress toward a demo-ready state.

## Infrastructure Assumptions

- Beelink + Pi5 are the current deployment/runtime targets.
- Near demo time, these devices may be repurposed to run newly built code.
- `CITADEL_BASE` in Eregion is aligned with the same base on main PC (not starting from zero).

## Documentation Requirement (Priority)

Create much clearer install instructions with explicit environment separation:

- Laptop development workflow
- Main PC (`Numenor Prime`) execution workflow
- Discord bridge troubleshooting and validation checks
- ATHENA bootstrapping sequence inside `Numenor Prime`
- CITADEL handoff/deployment sequence (Beelink + Pi5)
- "Day-0 to working" checklist with copy-paste commands

## Next Doc Deliverable

Rewrite install docs into a single practical guide with:

- Prerequisites
- Exact paths per machine
- Step-by-step commands
- Verification after each step
- Known failure points and fixes
