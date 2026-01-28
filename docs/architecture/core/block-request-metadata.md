# Block Request and Metadata

## Status
Draft

## Purpose
Define the canonical `Request` envelope passed to `Block.execute`, and standardize request/response `metadata` so execution can be traced, tested, and recovered deterministically.

## Scope
The `Request` model, metadata conventions, reserved keys, and propagation rules across nested (recursive) block execution.

## Contents

### Terminology
This document uses standardized terms defined in:
- [Block Glossary](block-glossary.md)

### Request Model
A `Request` is the standardized input envelope for `Block.execute`.

Fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `payload` | any | Block-specific input. The receiving block defines the expected shape. |
| `context` | dict | Pruned shared state relevant to the receiving block. The caller decides what to include. |
| `metadata` | dict | Execution metadata (tracing, attempt counters, policy hints). |

Requirements:
- A block MUST treat `payload`, `context`, and `metadata` as read-only inputs. If a block needs to "change" inputs, it must do so by creating a new request (for example during repair).
- A caller constructing a child request MUST prune `context` to the minimum necessary for the child.

### Metadata Conventions
Metadata exists to support observability, reproducibility, and recovery.

Observability expectations are defined in:
- [Block Observability](block-observability.md)

General rules:
- Reserved keys are defined in this document. Producers MUST NOT repurpose reserved keys.
- Non-reserved keys SHOULD be namespaced (for example: `"app.my_feature"`) to avoid collisions.
- If values may be serialized (logging, ledger, snapshots), metadata values SHOULD be JSON-serializable.

### Reserved Metadata Keys
These keys MAY appear in request and/or response metadata.

| Key | Type | Meaning |
| --- | --- | --- |
| `id` | str | Identifier for the request/response envelope. If present, MUST be globally unique enough for tracing/debugging (UUID recommended). |
| `trace_id` | str | Correlates all attempts within a single end-to-end operation (root run). |
| `span_id` | str | Correlates a single attempt of a single block execution. |
| `parent_span_id` | str | The parent span for nesting; empty/absent for the root attempt. |
| `run_id` | str | Correlates the full composite run (useful when a trace spans multiple runs). |
| `block_name` | str | The executing block's stable name. |
| `node_name` | str | The composite node name used to execute a child (only applicable in composites). |
| `attempt` | int | 1-based attempt counter for retries/repairs of the same block/node within a run. |
| `created_at` | str | Envelope creation time (ISO-8601). |
| `duration_ms` | int | Execution duration in milliseconds (responses only). |
| `side_effect_class` | str | Optional side-effect classification (`none`, `idempotent`, `non_idempotent`). |

Notes:
- This architecture does not require every reserved key to be present on every request/response.
- If a reserved key is present on a parent request, the caller SHOULD propagate it to child requests according to the propagation rules below.

Side effects:
- `side_effect_class` is optional but recommended when retry/repair decisions must survive serialization.
- Side-effect rules are defined in [Block Tool and Side-Effect Safety](block-tool-safety.md).

### Propagation Rules (Parent -> Child)
When a composite block constructs a child request, it SHOULD apply the following rules:

- `trace_id`: propagate unchanged.
- `run_id`: propagate unchanged.
- `parent_span_id`: set to the parent attempt's `span_id`.
- `span_id`: generate a new value for the child attempt.
- `attempt`: initialize to 1 on first execution; increment on retry/repair attempts of the same node.
- `block_name`: set to the child block's name (do not inherit the parent value).
- `node_name`: set to the composite node name used to select the child.
- `id`: generate a new envelope id for the child request.

### Response Metadata
Responses SHOULD include enough metadata to correlate outcomes back to the attempt that produced them.

Recommended minimum response keys:
- `trace_id`
- `span_id`
- `block_name`
- `attempt`
- `duration_ms`

### Serialization Guidance
Some runtime-only values (for example: exception classes) may not serialize. If a failure must be persisted or transmitted across process boundaries, the failure MUST include a stable string classifier (for example: `reason`) and any required structured fields in `details`.

## References
- [Core Architecture Index](index.md)
- [Block Glossary](block-glossary.md)
- [Block Architecture](block-interface.md)
- [Block Observability](block-observability.md)
- [Block Tool and Side-Effect Safety](block-tool-safety.md)
- [Block Responses](block-responses.md)
- [Block Architecture Open Questions](block-open-questions.md)
- [Architecture Index](../index.md)
