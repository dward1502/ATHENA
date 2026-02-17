# Architecture Decision: Mandatory Runtime Stack

Date: 2026-02-16
Status: Accepted

## Decision

The project will use the following as mandatory components:

- `picoclaw`
- `zeptoclaw`
- `RedPlanet Core`
- `OpenCode + oh-my-opencode`

These are not optional experiments; they are core to runtime feasibility.

## Why

- BluefinOS + Podman runtime on Beelink/Pi5 is resource constrained.
- `picoclaw`/`zeptoclaw` reduce RAM footprint materially.
- `RedPlanet Core` is required to preserve mission memory/context across sessions.
- `OpenCode + oh-my-opencode` is the CEO-to-ATHENA autonomous execution layer.

## Operational Model

- Main PC (`~/Numenor_prime`) is the company operations node.
- Discord is the CEO command/control interface.
- ATHENA operates within `Numenor_prime` to build and improve CITADEL.
- Beelink/Pi5 run Podman-based CITADEL workloads.

## Consequence

All implementation and documentation should be evaluated against this stack first.
If a change conflicts with this decision, it should be rejected or explicitly escalated.
