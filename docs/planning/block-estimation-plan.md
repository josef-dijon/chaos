# Block Estimation Plan

## Status
Draft

## Purpose
Define and implement a block-wide estimation API and stats interface, including a unified `BlockEstimate` contract and LLM proxy stats adaptation.

## Scope
In scope:
- Add `estimate_execution(request) -> BlockEstimate` to the Block interface.
- Define a `BlockEstimate` schema and semantics (cold-start priors, confidence).
- Add block stats recording + querying interfaces with a JSON/in-memory backend.
- Integrate estimation into `LLMPrimitive` via a LiteLLM stats adapter.
- Update architecture docs to reflect the new contracts.
- Add unit tests to keep coverage >= 95%.

Out of scope:
- Production Postgres backend (design should be swappable later).
- Graph-level orchestration changes unrelated to estimation.

## Contents

### Architecture References (Source of Truth)
- `docs/architecture/core/block-interface.md`
- `docs/architecture/core/block-request-metadata.md`
- `docs/architecture/core/block-responses.md`
- `docs/architecture/core/block-observability.md`
- `docs/architecture/core/block-recovery-semantics.md`
- `docs/architecture/core/02-llm-primitive.md`

### Implementation Targets

#### 1. BlockEstimate Contract
- Introduce a `BlockEstimate` model with:
  - identity/provenance (block_name, block_type, estimate_source, confidence, sample_size)
  - distributions (time/cost means + std devs)
  - counters (expected LLM calls, expected block executions)
- Require cold-start behavior (sample_size=0, low confidence, priors).

#### 2. Block Interface Extension
- Add `estimate_execution(request) -> BlockEstimate` to `Block`.
- Guarantee side-effect-free execution and deterministic results for a given stats snapshot.

#### 3. Stats Recording + Query Interfaces
- Add block-generic interfaces for recording attempt outcomes and querying aggregates.
- Provide a JSON/in-memory backend suitable for tests and development.
- Ensure client code does not depend on storage implementation.

#### 4. LLMPrimitive Estimation
- Add a LiteLLM stats adapter that translates proxy aggregates to `BlockEstimate`.
- Implement `LLMPrimitive.estimate_execution` with cold-start priors.

#### 5. Tests
- Unit tests for `BlockEstimate` validation and cold-start behavior.
- Tests for `Block.estimate_execution` default behavior (if provided).
- Tests for `LLMPrimitive.estimate_execution` with/without stats.
- Tests for stats recording/query interfaces (in-memory backend).

### Files Likely to Change
- `docs/architecture/core/block-interface.md`
- `docs/architecture/core/block-observability.md`
- `docs/architecture/core/02-llm-primitive.md`
- `docs/architecture/core/index.md`
- `docs/architecture/index.md`
- `src/chaos/domain/block.py`
- `src/chaos/domain/llm_primitive.py`
- `src/chaos/domain/block_estimate.py` (new)
- `src/chaos/stats/**` (new)
- `tests/**`

### Acceptance Criteria
- `Block` exposes `estimate_execution` with defined semantics.
- `BlockEstimate` is standardized and used by `LLMPrimitive`.
- Stats interfaces are storage-agnostic and backed by a JSON/in-memory implementation.
- Architecture docs reflect the new contracts.
- Test coverage remains >= 95%.

## References
- [Planning Index](index.md)
- [Core Architecture Index](../architecture/core/index.md)
- [Architecture Index](../architecture/index.md)
