# RedPlanet Core Integration (Verified)

Date verified: 2026-02-16

This file records the Core API contract used by `athena.py` so implementation is based on source docs, not assumptions.

## Verified Endpoints

- `GET /api/profile` - connectivity/auth sanity check
- `POST /api/v1/add` - persist memory entries
- `POST /api/v1/search` - memory retrieval (reserved for next phase)

## Auth Model

- Bearer token via `Authorization: Bearer <CORE_API_KEY>`

## ATHENA Runtime Env

- `CORE_API_KEY` (required in production)
- `CORE_API_BASE_URL` (optional, defaults to `https://core.heysol.ai`)
- `ATHENA_REQUIRE_CORE` (default strict mode is enabled unless set to `0`/`false`)

## Current Behavior in ATHENA

- By default, ATHENA fails fast when Core is unavailable.
- `--no-require-core` can be used for local testing only.
- Mission lifecycle events persisted:
  - objective received
  - battle plan created
  - deployment started
  - mission completed
- Planning uses Core retrieval before decomposition:
  - `POST /api/v1/search` on objective text
  - Optional ingestion refresh (`GET /api/v1/logs`) before planning to reduce stale reads
  - Retrieved context text influences component priority weighting/order
  - Weighting decision is persisted as `planning_priority_weighted`
  - Component templates are extracted from retrieved episodes (e.g., prior `components` payloads)
  - Relevant templates are merged into current planning and persisted as `planning_templates_applied`
  - Low-confidence results are filtered by configurable score thresholds

## Tuning Knobs (ATHENA CLI / env)

- `--core-score-threshold` / `ATHENA_CORE_SCORE_THRESHOLD`
- `--core-template-score-threshold` / `ATHENA_CORE_TEMPLATE_SCORE_THRESHOLD`
- `--core-refresh-before-plan` / `ATHENA_CORE_REFRESH_BEFORE_PLAN`
- `--core-refresh-timeout` / `ATHENA_CORE_REFRESH_TIMEOUT`

## Sources

- https://github.com/RedPlanetHQ/core
- https://docs.getcore.me/
- https://docs.getcore.me/api-reference
- https://docs.getcore.me/api-reference/get-user-profile
- https://docs.getcore.me/api-reference/add-memory
- https://docs.getcore.me/api-reference/search-memory
