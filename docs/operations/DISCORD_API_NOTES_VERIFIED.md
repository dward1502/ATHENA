# Discord API Notes (Verified)

Date verified: 2026-02-16

These notes were checked against official Discord docs and should guide bot behavior decisions.

## Message Content Intent

- Accessing message content for non-mention prefix commands requires Message Content intent.
- Current bot design (`!ulw`, `!athena`, etc.) depends on this intent being enabled in bot settings.

## Interactions Timing Constraint

- Interaction callbacks must send an initial response quickly (3-second window).
- If migrating from prefix commands to slash commands, long-running tasks should use deferred responses and follow-ups.

## Practical Impact for This Project

- Current prefix-command flow is valid but depends on privileged intent configuration.
- For robustness, a future migration to slash commands should defer and stream follow-up progress updates.

## Sources

- https://github.com/discord/discord-api-docs
- https://discord.com/developers/docs/topics/gateway
- https://discord.com/developers/docs/interactions/receiving-and-responding
