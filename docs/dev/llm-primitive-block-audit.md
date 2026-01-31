# LLM Primitive + Block Code Audit

## Status
Draft

## Purpose
Audit the current implementation of the `Block` and `LLMPrimitive` classes (and their supporting types) for logical correctness, architectural alignment, dead/unused code, test coverage gaps, and concrete improvement opportunities.

## Scope
In scope (primary):
- `src/chaos/domain/block.py`
- `src/chaos/domain/llm_primitive.py`

In scope (supporting):
- `src/chaos/domain/messages.py`
- `src/chaos/domain/policy.py`
- `src/chaos/domain/exceptions.py`
- `src/chaos/engine/policy_handlers.py`
- `src/chaos/engine/registry.py`
- `src/chaos/engine/conditions.py`
- `src/chaos/llm/llm_service.py`
- `src/chaos/llm/llm_error_mapper.py`
- `src/chaos/llm/stable_transport.py`
- `src/chaos/stats/*` (attempt records + estimation)
- Tests: `tests/domain/test_llm_primitive.py`

Out of scope:
- Higher-level agent runtime behavior beyond the block boundary.
- Refactors/behavior changes (this audit does not implement fixes).

## Contents

### Audit Plan (Executed)
1. Read architecture expectations for Blocks, recovery, metadata/observability, estimation, and LLMPrimitive semantics.
2. Inventory the concrete implementation entry points:
   - `Block.execute` and how it distinguishes leaf vs composite.
   - Graph execution semantics (validation, transitions, termination).
   - Recovery semantics (policy selection, attempt accounting, safety gates).
3. Audit request/response envelopes:
   - Reserved metadata keys and propagation.
   - Trace/span/attempt modeling.
4. Audit LLMPrimitive:
   - Payload coercion and message formation.
   - Error mapping taxonomy and recovery interaction.
   - Estimation vs stats recording correctness.
5. Audit supporting systems:
   - Repair registry and policy handling.
   - LLM transport retry and error mapping.
   - Stats store and estimate builder.
6. Audit tests:
   - Coverage of success/failure paths.
   - Coverage of composite recovery and repair behaviors.
7. Run the test suite and note coverage deltas/gaps.
8. Record findings and prioritized remediation recommendations.

### Key Findings (Prioritized)

#### Critical
1. Broken repair policy path: `LLMPrimitive.get_policy_stack` returns `RepairPolicy(repair_function="add_validation_feedback")`, but no repair function is registered anywhere.
   - Impact: Any composite caller attempting schema repair via `RepairPolicy` will fail deterministically (likely `reason=repair_execution_failed`) rather than repairing.
   - Evidence:
     - Policy stack in `src/chaos/domain/llm_primitive.py`.
     - `src/chaos/engine/registry.py` contains only the registry; no built-in registrations.
     - `src/chaos/engine/policy_handlers.py` requires `RepairRegistry.get(...)`.

2. Composite success responses drop trace/span/attempt metadata.
   - `Block._execute_graph` returns a new `Response` with metadata `{source, composite, last_node}` and does not preserve `trace_id`, `run_id`, `span_id`, `attempt`, or even the final node's response metadata.
   - Impact: Observability and correlation are lost at the composite boundary; downstream recovery selection and diagnostics become harder.
   - Evidence: `src/chaos/domain/block.py` composite terminal success path.

3. Repair/Debug policies are executed with the wrong request envelope and without attempt/span tracking.
   - `Block._execute_child_with_recovery` calls `PolicyHandler.handle(policy, node, request, current_failure)` using the *parent* request, not the `child_request` envelope containing `node_name`, `block_name`, `parent_span_id`, and `attempt`.
   - Additionally, attempts/spans are incremented only for the internal retry loop; repair/debug paths do not enforce attempt increments.
   - Impact: metadata invariants described by architecture are violated; attempt accounting becomes inconsistent and difficult to test.

#### Major
4. Recovery implementation is split between `Block` and `PolicyHandler` in a way that creates dead paths and inconsistent semantics.
   - `PolicyHandler.retry(...)` exists but `Block` does not use it; `Block` implements retries internally for `RetryPolicy`.
   - Repair handling is delegated but receives incorrect request metadata (see Critical #3).
   - Impact: duplicated logic, higher defect risk, and lower testability.

5. Retry attempt semantics are ambiguous and likely inconsistent with the architectural phrasing "up to max_attempts".
   - Current behavior: one initial call + `RetryPolicy.max_attempts` additional calls.
   - If `max_attempts` is intended as total attempts (including initial), this is an off-by-one.
   - If `max_attempts` is intended as retries (excluding initial), the naming/documentation should make that explicit.

6. `LLMPrimitive` performs internal semantic repair loops that overlap with (and can multiply) block-level recovery.
   - Internal loop retries on `ResponseStatus.SEMANTIC_ERROR` up to `max_repair_attempts`.
   - Separately, `get_policy_stack(SchemaError)` also proposes retries/repairs.
   - Impact: unexpected call amplification and unclear ownership of repair semantics.

7. `LLMPrimitive` stats recording does not reflect actual LLM usage.
   - `_build_attempt_record` hard-sets `llm_calls=1` and records `model=self._model` even if a selector chose a different model.
   - Internal repair loops can perform multiple LLM calls, but only one attempt record is written per `Block.execute` call.
   - Impact: stats-derived estimates undercount cost/time/llm_calls and can mislead downstream tuning.

8. Graph validation/condition resolution failures surface as `internal_error` instead of a stable "invalid graph" failure response.
   - `_validate_graph` can raise (e.g., unresolved condition id); `execute(...)` catches and returns `internal_error`.
   - Impact: callers cannot reliably distinguish invalid configuration from runtime errors.

#### Minor / Design Smells
9. `Block.__init__` calls `self.build()` during base initialization.
   - Today, only `LLMPrimitive.build()` exists (no-op), so no immediate bug.
   - Risk: future subclasses overriding `build()` may rely on attributes not yet set (common Python init pitfall).

10. Default config appears internally inconsistent for a proxy workflow.
   - `Config.litellm_use_proxy` defaults to true while `litellm_proxy_url` defaults to `None`.
   - `scripts/llm_primitive_demo.py` requires `openai_api_key` even though a proxy workflow might not.
   - Impact: confusing defaults and demo behavior.

11. Error type taxonomy is not fully normalized.
   - `map_llm_error(...)` will return `error_type=type(error)` for unknown exceptions; this may be a provider exception type.
   - Impact: recovery selection based on `error_type` becomes unstable across providers/versions.

### Unused or Effectively Unused Code
- `PolicyHandler.retry(...)` in `src/chaos/engine/policy_handlers.py` is not used by `Block`'s recovery path.
- `RepairRegistry` / `PolicyHandler.repair(...)` appear unexercised by tests and currently have no registered repair functions.
- `ModelSelector` in `src/chaos/llm/model_selector.py` is currently a placeholder (returns default model).

### Test Coverage Notes
The suite passes and meets the project-wide 95% coverage bar (`uv run pytest -q`). The specific areas most relevant to this audit remain under-tested:
- `src/chaos/domain/block.py` recovery branches and invalid-graph responses.
- `src/chaos/engine/policy_handlers.py` (repair, debug, retry paths).
- `src/chaos/llm/llm_service.py` and `src/chaos/llm/llm_error_mapper.py` for non-happy-path transport and mapping scenarios.

### Recommended Remediation Plan (Concrete)

1. Fix the repair story (pick one of these directions):
   - A. Make repair policies real: implement and register `add_validation_feedback` (and any other referenced repair functions) in `RepairRegistry`, and ensure it transforms the Request deterministically.
   - B. Remove repair policies from `LLMPrimitive.get_policy_stack` and rely only on its internal semantic repair loop.
   - C. Remove internal repair loops and rely solely on block recovery (`RepairPolicy` + `RetryPolicy`) so behavior is uniform whether the primitive is called directly or inside a composite.

2. Normalize recovery execution to a single place.
   - Either:
     - Move all recovery execution into `PolicyHandler` (and have `Block` delegate for *all* policy types), or
     - Keep all recovery execution in `Block` and make `PolicyHandler` a thin helper invoked with the correct child request and updated attempt/span metadata.
   - Ensure repair and debug attempts increment `attempt` and create new `span_id` the same way retries do.

3. Preserve required metadata in composite responses.
   - Composite responses should include at least `trace_id`, `run_id`, `span_id`, `block_name`, `attempt`, and `duration_ms`.
   - Decide whether to return the last node's response metadata merged, or a composite-owned envelope that still propagates correlation keys.

4. Make graph validation failures stable and deterministic.
   - Convert condition resolution/graph validation exceptions into `Response(success=False, reason=invalid_graph, error_type=Exception, details=...)` (or a dedicated `InvalidGraphError`).
   - Prefer validating/resolving in `build()` (or a dedicated validation step) rather than at first execution.

5. Make stats recording and estimation honest.
   - `LLMPrimitive` should record actual selected model and actual number of LLM calls per execution (including internal repairs).
   - Consider threading LLM usage (tokens/cost) from `LLMResponse.usage` into the `BlockAttemptRecord`.

6. Tighten error type normalization.
   - Ensure `LLMPrimitive` emits only stable domain error types for its documented failure classes.
   - Preserve underlying causes in `details` while keeping `error_type` stable for recovery selection.

7. Add targeted tests for recovery + metadata invariants.
   - New tests for `Block` composite recovery: retries increment attempt; repairs generate new request; bubble returns unchanged.
   - Tests for missing repair function should fail fast and clearly.
   - Metadata assertions for composite and leaf blocks (trace/span/attempt propagation).

## References
- `docs/architecture/core/index.md`
- `docs/architecture/core/block-interface.md`
- `docs/architecture/core/block-recovery-semantics.md`
- `docs/architecture/core/block-request-metadata.md`
- `docs/architecture/core/02-llm-primitive.md`
- `docs/architecture/index.md`
- `docs/dev/index.md`
