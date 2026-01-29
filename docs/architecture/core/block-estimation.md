# Block Estimation

## Status
Draft

## Purpose
Define the estimation contract for blocks, including the `BlockEstimate` schema, cold-start behavior, and determinism requirements.

## Scope
Block-level estimation semantics, required fields, and how estimates are derived from statistics or priors. This document does not define storage or database implementations.

## Contents

### Terminology
This document uses standardized terms defined in:
- [Block Glossary](block-glossary.md)

### 1. Estimation API
Every `Block` MUST expose:

```
estimate_execution(request: Request) -> BlockEstimate
```

Normative rules:
- `estimate_execution` MUST be side-effect free.
- `estimate_execution` MUST return a `BlockEstimate` for any input.
- `estimate_execution` SHOULD be deterministic for a given request and a given statistics snapshot.

### 2. BlockEstimate Schema (Required Fields)
`BlockEstimate` is a structured estimate of expected execution footprint.

Required fields:
- `block_name` (str): stable instance name.
- `block_type` (str): stable type identifier (for example: `llm_primitive`).
- `estimate_source` (str): `stats`, `prior`, `heuristic`, or `unknown`.
- `confidence` (str): `low`, `medium`, or `high`.
- `sample_size` (int): number of historical samples used.
- `time_ms_mean` (float)
- `time_ms_std` (float)
- `cost_usd_mean` (float)
- `cost_usd_std` (float)
- `expected_llm_calls` (float)
- `expected_block_executions` (float)

Optional fields:
- `version` (str | None): version of the block logic.
- `components` (dict[str, BlockEstimate] | None): breakdown for composites.
- `notes` (list[str]): assumptions or caveats.

### 3. Cold-Start Semantics
When no historical stats exist, the block MUST return a prior-based estimate:
- `sample_size = 0`
- `estimate_source = "prior"`
- `confidence = "low"`
- means/std devs are conservative defaults appropriate to the block

Cold-start estimates MUST NOT fail or return a sentinel error.

### 4. Determinism and Inputs
Estimates SHOULD be deterministic for a given request and statistics snapshot. Blocks may use request features (for example: prompt length, schema complexity) to refine estimates.

### 5. LLM-Specific Extensions
LLM-backed blocks MAY include LLM-specific hints in `notes` or attach a component breakdown that includes:
- expected input/output tokens
- selected model identifier

These are optional and must not change the required schema fields.

## References
- [Core Architecture Index](index.md)
- [Block Glossary](block-glossary.md)
- [Block Architecture](block-interface.md)
- [Block Observability](block-observability.md)
- [Block Request and Metadata](block-request-metadata.md)
- [Block Responses](block-responses.md)
- [Architecture Index](../index.md)
