# Block Interface Plan

## Status
Draft

## Purpose
Plan the implementation of the core block interface and its test coverage.

## Scope
Core interface structure under `src/chaos/`, abstract `IBlock` definition, and unit tests.

## Contents

### Goal
Implement the core `IBlock` interface in `src/chaos/` and prove it with unit tests.

### Deliverables
- Core package structure under `src/chaos/core/`.
- `IBlock` interface definition with documented state transitions.
- Unit tests covering abstract enforcement and a minimal concrete implementation.

### Constraints
- Follow one-class-per-file and docstring requirements.
- No runtime config changes; keep implementation minimal and testable.
- Use `uv` for running tests.

### Steps
1. Create `src/chaos/core/` package structure and the `IBlock` interface file.
2. Implement `BlockState` enum and document state transitions in the interface.
3. Add unit tests for abstract enforcement and minimal subclass behavior.
4. Run tests with `uv run pytest` and fix failures if any.

## References
- [Core Architecture Index](../architecture/core/index.md)
- [Architecture Index](../architecture/index.md)
