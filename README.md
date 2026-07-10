# Team Memory

**Shared memory for coding agents.** One team, one memory — powered by [Supermemory Local](https://supermemory.ai/docs/self-hosting/overview).

Built for the Supermemory **localhost:6767** hackathon (July 9–13, 2026).

## The idea

Every developer's coding agent (Claude Code, Codex, Cursor, ...) starts every session knowing nothing your teammates' agents already learned. Team Memory is an MCP server backed by Supermemory Local that gives all agents on a team one shared brain:

- **`recall`** — before starting a task, an agent pulls the team's relevant decisions, gotchas, and failed approaches.
- **`remember`** — when an agent learns something non-obvious, it saves the lesson for everyone, with provenance (who, when, at which commit).
- **`whats_happening` / `claim_work`** — agents see what teammates' agents are working on right now and avoid conflicting edits.

Everything runs on your own machine — your team's memory never leaves your network.

## Status

🚧 Hackathon build in progress.
