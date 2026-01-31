# Python Review Agent Plan

## Status
In Progress

## Purpose
Define and implement a Python-specific review agent and slash command that run a rigorous, multi-pass code and documentation review for any area of a Python codebase. Reviews must be stored in timestamped directories under `docs/reviews/` and must cover both Python modules and any related JSON/YAML files that those modules load or mutate.

## Scope
- Review orchestration:
  - Master review agent in `~/.config/opencode/agents/`.
  - Slash command in `~/.config/opencode/commands/` that accepts a single description argument.
- Review outputs:
  - Store all review artifacts in `docs/reviews/<YYYY-MM-DD-HHMMSS>/`.
  - Separate per-lens review files plus a collated master review file.
- Review criteria:
  - Architecture/SOLID, clean boundaries, modularity.
  - Error handling and recovery semantics.
  - Testability and coverage fitness.
  - DRY and dead code removal.
  - Modern Python best practices, typing, docstrings.
  - Naming, readability, maintainability.
  - Logging/observability with a strict logging standard.
  - Documentation accuracy, completeness, and architecture alignment.
- Scope discovery:
  - Python modules matching the request plus associated JSON/YAML or other config files used by those modules.

## Contents
### Plan
1. Define review lenses and the logging standard used across all reviews.
2. Implement a master review agent that:
   - Resolves scope from the description.
   - Creates the timestamped review directory.
   - Launches subagents per review lens.
   - Collates findings into a single master review document.
3. Implement subagent prompt templates that:
   - Enforce incremental writes (append findings immediately).
   - Use a consistent finding format (severity, file, issue, impact, fix).
4. Implement the `/review` command file that:
   - Accepts a single argument for the review description.
   - Delegates to the master review agent.
5. Update `docs/planning/index.md` to track the plan and checklist.

### Outputs
- `docs/planning/python-review-agent-plan.md`
- `docs/planning/python-review-agent-checklist.md`
- `~/.config/opencode/agents/python-review-master.md`
- `~/.config/opencode/commands/review.md`

## References
- `docs/planning/index.md`
- `docs/architecture/index.md`
- `docs/documentation-standard.md`
