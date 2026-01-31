# LLM Primitive + Block Audit Plan

## Status
Complete

## Purpose
Provide a repeatable audit procedure for reviewing the `Block` runtime contract and the `LLMPrimitive` leaf block implementation, including recovery behavior, metadata/observability, estimation/statistics correctness, and test coverage.

## Scope
- Code: `src/chaos/domain/block.py`, `src/chaos/domain/llm_primitive.py`, and supporting recovery/LLM/stats modules.
- Docs: core architecture docs for Blocks and LLMPrimitive.
- Tests: `tests/domain/test_llm_primitive.py` plus any coverage notes.

## Contents
### Plan
1. Establish architectural expectations:
   - Block execution and graph semantics.
   - Recovery semantics and safety gates.
   - Request/response metadata requirements.
   - Estimation and stats recording contract.
   - LLMPrimitive-specific semantics.
2. Inventory code entry points and invariants:
   - `Block.execute`, `_execute_graph`, `_execute_child_with_recovery`.
   - Policy selection (`get_policy_stack`) and policy execution.
3. Map supporting systems:
   - Condition registry.
   - Policy handler and repair registry.
   - LLM service, transport, and error mapping.
   - Stats store and estimate builder.
4. Identify correctness issues:
   - Spec mismatches.
   - Logical inconsistencies.
   - Dead/unused code or missing implementations.
5. Validate test coverage and add test recommendations.
6. Run `uv run pytest -q` to confirm baseline behavior.
7. Write a single audit report with prioritized remediation recommendations.

### Outputs
- Audit report: `docs/dev/llm-primitive-block-audit.md`

## References
- `docs/planning/index.md`
- `docs/dev/llm-primitive-block-audit.md`
