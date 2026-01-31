# Error Handling Review

Timestamp: 2026-01-31-145336

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: `unknown_node` failures return a Response without `error_type` set (line ~204), despite `error_type` being the canonical recovery selector.
  Impact: Upstream recovery policy selection will silently fall back to a generic Exception, losing deterministic error classification and making failure handling inconsistent.
  Recommendation: Set `error_type` explicitly (for example `Exception` or a dedicated graph error class) on the `unknown_node` response.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: `RetryPolicy.delay_seconds` is never honored in `_execute_child_with_recovery` (retry loop runs back-to-back with no delay or jitter).
  Impact: Retries can hammer providers and amplify rate-limit/mechanical failures; violates recovery policy backoff expectations.
  Recommendation: Sleep between retries using `delay_seconds` (with optional jitter), or explicitly document that delay is unsupported and remove the field.
  Architecture alignment: No

- Severity: High
  File: src/chaos/domain/block.py
  Issue: Repair handling drops the repaired request metadata by copying only `payload`/`context` onto a clone of the original parent request (`repaired_parent_request`), instead of using the `Request` returned by the repair function.
  Impact: Any recovery metadata or correlation hints added by the repair function are silently lost, making repair diagnostics and subsequent policy selection unreliable.
  Recommendation: Use the `Request` returned from the repair function as the basis for the retry, and only override/propagate reserved metadata fields explicitly if needed.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: When retry/repair is unsafe, `_execute_child_with_recovery` returns a new `unsafe_to_retry` Response, discarding the original failure `reason`/`details`.
  Impact: The caller loses the root cause and cannot distinguish between the underlying failure vs. a recovery-policy veto, complicating incident analysis and policy tuning.
  Recommendation: Preserve the original failure (for example by returning it with an added `details.recovery_blocked=true` or by embedding the original failure under `details.original_failure`).
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Condition evaluation exceptions (`condition_func(response)`) are not caught during transition selection, so a condition bug throws and is translated into a generic `internal_error` in `Block.execute`.
  Impact: The failure reason loses the condition name and becomes opaque to recovery policies and debugging.
  Recommendation: Catch exceptions around condition execution and return a structured failure (for example `reason=condition_evaluation_error`, with `details.condition` and the exception string).
  Architecture alignment: No

- Severity: Low
  File: src/chaos/domain/block.py
  Issue: If a block implementation accidentally returns `None`, `execute` constructs an `internal_error` Response after the `finally` block, so no correlation metadata is attached and no attempt is recorded.
  Impact: The most severe class of contract violation (returning None) is invisible to observability/metrics, making recovery and diagnosis harder.
  Recommendation: Create the fallback `internal_error` Response before `finally` exits (or in `finally`) so metadata and attempt records are always captured.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/llm/llm_service.py
  Issue: `_run_agent` raises a `TypeError` for unexpected output types, which maps via `map_llm_error` to a generic mechanical failure instead of a structured schema/semantic error.
  Impact: Recovery policies and analytics misclassify malformed model output as transient infrastructure failure, obscuring root cause and policy tuning.
  Recommendation: Map unexpected output types to `SchemaError` (or wrap in a dedicated exception) so `LLMResponse` is categorized as `SEMANTIC_ERROR`.
  Architecture alignment: Yes

- Severity: Medium
  File: src/chaos/stats/json_block_stats_store.py
  Issue: `_load` assumes the JSON file is valid; corrupt or partially-written stats files raise `json.JSONDecodeError` during store initialization with no recovery path.
  Impact: A single corrupted stats file can prevent the system from starting, even though stats are non-critical.
  Recommendation: Catch JSON decode/validation errors, log a warning, and start with an empty record set or a quarantined backup.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: `_execute_child_with_recovery` defaults to `Exception` when `response.error_type` is missing, instead of using a deterministic fallback mapping (for example, from `response.reason`).
  Impact: Serialized or partially-constructed failures lose recovery specificity, causing policy selection to degrade to the generic stack.
  Recommendation: Add a fallback classifier (e.g., map from `reason` to an error type) when `error_type` is absent.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/llm/llm_error_mapper.py
  Issue: Unknown exceptions are mapped with `error_type=type(error)`, which can be provider-specific and unstable across versions.
  Impact: Recovery policy selection becomes non-deterministic across environments and upgrades, making automated recovery brittle.
  Recommendation: Normalize unknown errors to a stable domain exception (for example `LLMError` or a new `UnknownLLMError`) while preserving the original class name in `details`.
  Architecture alignment: No

- Severity: Low
  File: tests/domain/test_llm_primitive.py
  Issue: Recovery semantics are largely untested (no coverage for retry/repair paths, unsafe-to-retry behavior, or error_type-missing fallback selection).
  Impact: Error handling regressions can ship unnoticed, especially in composite recovery flows.
  Recommendation: Add focused tests for retry delays, repair metadata propagation, and policy selection when `error_type` is absent.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/stats/store_registry.py
  Issue: The default stats store is instantiated at import time, so any JSON parse error or filesystem issue raises during module import with no recovery.
  Impact: Non-critical stats corruption can prevent the entire runtime from starting, and the failure path is hard to recover from in callers.
  Recommendation: Lazily initialize the default store inside `get_default_store()` with guarded error handling and a safe fallback (for example in-memory store).
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/messages.py
  Issue: `Request.payload` is typed as `Dict[str, Any]`, but LLMPrimitive expects `payload` to be either a string or a dict; a string payload will fail validation before error handling can run.
  Impact: Invalid payloads raise Pydantic validation errors outside the block boundary, bypassing the standardized failure responses and recovery policies.
  Recommendation: Widen `Request.payload` to `Any` (or `str | dict`) and let blocks validate/normalize payloads into their own error responses.
  Architecture alignment: No

- Severity: Low
  File: src/chaos/domain/block.py
  Issue: `_record_attempt` swallows all exceptions without logging or surfacing any signal.
  Impact: Stats persistence failures are silent, making it impossible to detect missing attempt records that feed recovery/estimation logic.
  Recommendation: Log a warning (or emit a telemetry event) when attempt recording fails, including the exception and block identity.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: The `manager_id` created for LLM auditing is stored only in the internal `LLMRequest` metadata and is not surfaced in the block `Response` metadata.
  Impact: When failures occur, there is no stable identifier to correlate provider-side logs/requests with block-level errors, reducing recovery and debugging effectiveness.
  Recommendation: Copy `manager_id` into `Response.metadata` (for both success and failure) under a namespaced key (e.g., `llm.manager_id`).
  Architecture alignment: Unknown
