# Ledger Checkpoints and Rollback

## Status
Draft

## Purpose
Describe transactional ledger checkpoints and rollback behavior for deep diagnostics.

## Scope
Checkpoint timing, retention, and rollback flow.

## Contents

### State Management: The Transactional Ledger
To support deep diagnostics and rollbacks, the manager acts as a transactional engine.

#### Checkpointing
- When: before executing any child block.
- What: snapshot of current context/ledger.
- Retention: snapshots persist for the duration of container execution.
- Purge: snapshots discarded after the container returns success (or when compacted).

#### Snapshot Naming
- Use deterministic ids tied to execution steps (e.g., `pre_step_b`).
- Keep a small rolling window for long-running containers.

#### Rollback Mechanism
When a deep diagnostic strategy requests a rollback to Step B:
1. Manager pauses execution.
2. Manager retrieves `Snapshot_Pre_Step_B`.
3. Manager overwrites current context with snapshot.
4. Manager applies the fix to Step B input.
5. Manager resumes execution from Step B.

## References
- [Core Architecture Index](index.md)
- [Architecture Index](../index.md)
