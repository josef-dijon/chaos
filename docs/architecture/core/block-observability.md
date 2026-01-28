# Block Observability

## Status
Draft

## Purpose
Define the minimum observability surface (tracing identifiers and events) for block execution and recovery.

## Scope
Trace/span model, metadata requirements, and a minimal event vocabulary for logs/telemetry.

## Contents

### Terminology
This document uses standardized terms defined in:
- [Block Glossary](block-glossary.md)

### Trace Model
The architecture uses a simple trace model:

- `trace_id`: groups the full end-to-end operation.
- `run_id`: groups a single composite run.
- `span_id`: identifies a single block attempt.
- `parent_span_id`: identifies the parent attempt.

See reserved keys:
- [Block Request and Metadata](block-request-metadata.md)

### Metadata Requirements
To make composite runs debuggable, the runtime MUST be able to correlate attempts and outcomes.

Minimum requirements:
- Every response MUST include `metadata.block_name`.
- Every response SHOULD include `metadata.trace_id` and `metadata.span_id`.
- Every response SHOULD include `metadata.attempt` for nodes that can be retried or repaired.

### Correlation With Ledger Provenance
If the ledger is used, ledger entry provenance SHOULD include:
- `trace_id`
- `run_id`
- `span_id`
- `block_name`
- `node_name` (if written by a composite from a child result)
- `attempt`

### Event Vocabulary (Recommended)
Events are intended for logs and telemetry.

Recommended event types:
- `block_start`
- `block_success`
- `block_failure`
- `recovery_start`
- `recovery_policy_start`
- `recovery_policy_exhausted`
- `recovery_success`
- `recovery_failure`
- `ledger_checkpoint_created`
- `ledger_rollback`

Recommended event fields:
- `trace_id`, `run_id`, `span_id`, `parent_span_id`
- `block_name`, `node_name`
- `attempt`
- `reason` (for failures)

## References
- [Core Architecture Index](index.md)
- [Block Glossary](block-glossary.md)
- [Block Request and Metadata](block-request-metadata.md)
- [Block Responses](block-responses.md)
- [State Ledger](03-state-ledger.md)
- [Architecture Index](../index.md)
