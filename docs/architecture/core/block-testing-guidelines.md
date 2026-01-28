# Block Testing Guidelines

## Status
Draft

## Purpose
Define how to test leaf and composite blocks deterministically, including recovery paths, without real network/tool calls.

## Scope
Unit testing recommendations, mocking strategy, and suggested golden tests for composite execution traces.

## Contents

### Terminology
This document uses standardized terms defined in:
- [Block Glossary](block-glossary.md)

### General Rules
- Tests MUST be deterministic.
- Tests MUST NOT make real network calls.
- LLM calls MUST be mocked.

### Testing Leaf Blocks
For each leaf block:

- Test success path returns `Response` where `success()` is `True` and `data` matches.
- Test failure path returns `Response` where `success()` is `False` and includes stable `reason` + structured `details`.
- Test that expected failures are represented as responses, not exceptions.

### Testing Composite Blocks
Composite blocks should be tested using stub child blocks:

- Use a stub block that deterministically returns successful/failed `Response` values based on input.
- Test transition selection (linear and branching).
- Test `max_steps` protection returns `Response` with `reason="max_steps_exceeded"`.

### Testing Recovery
Recovery should be tested by forcing deterministic child failures:

- Retry: configure child to fail N-1 times then succeed; assert `attempt` increments.
- Repair: configure a repair function to transform the request; assert the repaired request is used.
- Bubble: configure child policy stack to bubble; assert failure propagates unchanged.

See:
- [Block Recovery Semantics](block-recovery-semantics.md)

### Time and Backoff
If retry backoff is implemented:

- Use a fake clock or patch sleep so tests run fast.
- Assert backoff decisions via captured calls rather than real waiting.

### Metadata Assertions
At minimum, tests SHOULD verify:
- `block_name` is present on responses
- `trace_id`/`span_id` propagate or are generated deterministically in tests

See:
- [Block Request and Metadata](block-request-metadata.md)
- [Block Observability](block-observability.md)

## References
- [Core Architecture Index](index.md)
- [Block Glossary](block-glossary.md)
- [Block Request and Metadata](block-request-metadata.md)
- [Block Observability](block-observability.md)
- [Block Responses](block-responses.md)
- [Block Execution Semantics](block-execution-semantics.md)
- [Block Recovery Semantics](block-recovery-semantics.md)
- [Architecture Index](../index.md)
