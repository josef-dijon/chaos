# PydanticAI Pre-Migration Stabilization Plan (Complete)

## Status
Complete

## Purpose
Stabilize the current Block + LLMPrimitive runtime before the PydanticAI migration by resolving the audit items that are correctness/observability issues independent of the instructor/tenacity stack.

This is intended to (1) remove known deterministic failure paths, and (2) lock down behavior with tests so the migration can be validated against stable invariants.

## Scope
- Code:
  - `src/chaos/domain/llm_primitive.py`
  - `src/chaos/domain/block.py` (composite boundary + graph validation surfaces)
  - Recovery/policy plumbing as needed for the items below
- Docs (only if gaps/spec mismatches are found):
  - `docs/architecture/core/02-llm-primitive.md`
  - `docs/architecture/core/recovery-policy-system.md`
  - `docs/architecture/core/block-request-metadata.md`
  - `docs/architecture/core/block-observability.md`
  - `docs/architecture/core/block-responses.md`
- Tests: unit tests covering the invariants below (mock all LLM calls).

### In Scope Audit Items (Fix Now)
1. Broken repair reference: `RepairPolicy(repair_function="add_validation_feedback")` exists in the policy stack but no repair function is registered.
2. Composite success metadata loss: trace/span/attempt (and correlation metadata) must survive composite boundaries.
3. Wrong request envelope for repair/debug policies: repair/debug must operate on the `child_request` and must be tracked like attempts.
4. Invalid graph failures: graph validation failures must return a stable invalid-graph response (not `internal_error`).

### Out of Scope (Defer to Migration Plan)
- Removing `tenacity` / `instructor`.
- Changing retry semantics or moving retry responsibility (PydanticAI will own API retry + schema retry post-migration).
- Removing/rewriting the internal semantic repair loop.
- Broad recovery refactors (e.g., unifying Block vs PolicyHandler) beyond what is strictly required for the fixes above.
- Full stats/usage overhaul.

## Contents
### Plan
1. Reconfirm architectural intent (spec first):
   - Ensure the architecture explicitly defines:
     - Required request/response correlation metadata propagation across parent/child and composite boundaries.
     - What constitutes a stable invalid-graph failure category.
     - How attempts/spans are represented and when they increment.
   - If the spec is missing or ambiguous, update the relevant architecture docs before code changes.
2. Fix the broken repair policy reference (pick one, document it, and test it):
   - Option A (preferred for safety): remove the policy from `LLMPrimitive.get_policy_stack` until a real repair function exists.
   - Option B: implement and register `add_validation_feedback` in the repair registry and add a unit test proving it is callable and wired.
3. Preserve correlation metadata across composite success responses:
   - Ensure success responses from composite execution include the trace/span/attempt metadata from the executed leaf/child.
   - Add unit tests that assert metadata is present and stable across the composite boundary.
4. Correct the request envelope used by repair/debug policies:
   - Ensure policy execution uses the `child_request` (not the parent request).
   - Ensure repair/debug attempts are tracked consistently (attempt id/span id behavior should match retry attempt tracking semantics).
   - Add unit tests covering:
     - The request passed into policy execution.
     - Attempt/span tracking on repair/debug.
5. Stabilize invalid graph failures:
   - Convert graph validation exceptions into the stable invalid-graph response category defined in the architecture.
   - Add unit tests that assert invalid graph surfaces as invalid-graph (not `internal_error`).
6. Verification:
   - Run `uv run pytest` and confirm coverage >= 95%.
   - Record any follow-up deltas that become migration prerequisites.

### Outputs
- Code changes implementing the four fixes.
- Unit tests that lock down the invariants.
- Architecture doc updates only if needed to clarify required behavior.

## References
- `docs/planning/index.md`
- `docs/dev/llm-primitive-block-audit.md`

## Completion Notes
- Implemented and registered the missing `add_validation_feedback` repair.
- Preserved correlation metadata across composite boundaries and debug/repair policy execution.
- Stabilized condition resolution failures.
- Added unit tests for these invariants and confirmed coverage >= 95%.
