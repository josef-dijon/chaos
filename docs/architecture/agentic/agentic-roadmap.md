# Agentic Roadmap

## Status
Draft

## Purpose
Capture the staged rollout from CLI prototype to multi-agent and Mattermost integration.

## Scope
MVP, team scaling, and view layer integration milestones.

## Contents

### MVP (CLI Prototype)
Initial implementation is a Python CLI for rapid iteration on memory and learning logic.

- Architect interacts with a single Chaos agent (e.g., a coder persona).
- `do` command uses standard input.
- `learn` and `dream` are manual triggers.
- Output is color-coded to simulate mirror persona (Actor = green, Subconscious = blue).

### Scaling to a Team
Multiple Agent instances communicate via the `do()` API. Each subconscious monitors inter-agent communications and triggers learn cycles if the team dynamic breaks down.

### Mattermost View Layer
Future digital headquarters integrates CHAOS into Mattermost.

- Actor posts as a standard bot user in public channels.
- Subconscious appears in training GDMs or as a mirror alias in private threads during learn mode.
- Identity management uses Mattermost Playbooks to view health and instructions.

## References
- [Agentic Architecture Index](index.md)
- [Architecture Index](../index.md)
