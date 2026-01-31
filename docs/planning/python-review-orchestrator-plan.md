# Python Review Orchestrator Rework Plan

## Status
In Progress

## Purpose
Refactor the Python review agent so the primary agent only orchestrates subagents, delegates all pre/post steps, and expands review lenses into more granular perspectives. The primary agent should be directly invokable from the opencode prompt without a separate command.

## Scope
- Primary review agent behavior and configuration.
- New orchestration subagents for scope discovery, review scaffolding, and collation.
- Granular review lenses to address gaps (security/privacy, performance/scalability, dependency/config hygiene).
- De-emphasize command-based invocation in favor of a primary agent.

## Contents
### Plan
1. Define the new orchestration flow and review lens gaps to cover.
2. Implement orchestration subagents:
   - Scope discovery
   - Review scaffolding (directory + per-lens file creation)
   - Master collation
3. Split additional-risks coverage into granular review lenses.
4. Rename and update the primary review agent to be an orchestrator-only, tool-less, primary mode agent.
5. Update command invocation guidance to align with the primary agent usage.
6. Update planning index.

### Outputs
- `docs/planning/python-review-orchestrator-plan.md`
- `docs/planning/python-review-orchestrator-checklist.md`
- `~/.config/opencode/agents/python-review.md`
- `~/.config/opencode/agents/python-review-scope.md`
- `~/.config/opencode/agents/python-review-scaffold.md`
- `~/.config/opencode/agents/python-review-collate.md`
- `~/.config/opencode/agents/python-review-security.md`
- `~/.config/opencode/agents/python-review-performance.md`
- `~/.config/opencode/agents/python-review-dependencies.md`
- `~/.config/opencode/commands/pyreview.md` (updated or removed)

## References
- `docs/architecture/index.md`
- `docs/architecture/agentic/index.md`
- `docs/planning/index.md`
