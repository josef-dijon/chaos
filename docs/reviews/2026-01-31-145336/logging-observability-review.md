# Logging and Observability Review

Timestamp: 2026-01-31-145336

- Severity: High
  File: src/chaos/domain/block.py
  Issue: Composite responses keep child `metadata.block_name`/`span_id` and never overwrite them with the composite attempt identifiers.
  Impact: Observability breaks at composite boundaries because callers cannot correlate a composite attempt (trace/run/span/attempt) to the returned response; the response appears to be from the child only.
  Recommendation: When a composite returns a response, explicitly set composite correlation metadata (`block_name`, `span_id`, `attempt`, `run_id`, `trace_id`, `node_name` as applicable) rather than using `setdefault` so the composite attempt is represented.
  Architecture alignment: No

- Severity: Low
  File: src/chaos/domain/block.py
  Issue: Composite success responses add un-namespaced metadata keys (`source`, `composite`, `last_node`) that are not part of the reserved set.
  Impact: Metadata collisions and inconsistent log fields make observability queries brittle across blocks.
  Recommendation: Namespace composite-specific metadata (for example `composite.source`, `composite.name`, `composite.last_node`).
  Architecture alignment: No

- Severity: Low
  File: tests/domain/test_llm_primitive.py
  Issue: Tests do not assert required observability metadata fields (`trace_id`, `run_id`, `span_id`, `block_name`, `attempt`, `duration_ms`) on responses.
  Impact: Correlation regressions can slip in without detection, weakening observability guarantees.
  Recommendation: Add tests that validate presence and propagation of required metadata on success and failure paths.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: Response metadata uses non-namespaced keys (`model`, `llm_usage`, `llm_calls`, `llm_retry_count`, `input_tokens`, `output_tokens`) despite the metadata standard requiring namespacing for non-reserved keys.
  Impact: Inconsistent metadata conventions make it harder to filter/aggregate logs and risk collisions with other producers.
  Recommendation: Namespace these fields (for example `llm.model`, `llm.usage`, `llm.calls`, `llm.retry_count`, `llm.input_tokens`, `llm.output_tokens`).
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/llm/llm_error_mapper.py
  Issue: Error details embed `str(error)` and `str(cause)` verbatim without redaction or size bounds.
  Impact: Exception strings can include raw prompts, payload fragments, or credentials, which risks PII/secret leakage when these details are logged or persisted.
  Recommendation: Sanitize/redact sensitive fields (API keys, prompts, payloads) and enforce a maximum length before storing error details.
  Architecture alignment: No

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: Internal retry metadata keys (`block_attempt`, `llm_attempt`) are not namespaced even though the metadata standard requires non-reserved keys to be namespaced.
  Impact: These keys can collide with other metadata producers and are harder to search/aggregate consistently.
  Recommendation: Rename to namespaced keys like `llm.block_attempt` and `llm.attempt` (or a project-specific namespace) and update any downstream consumers.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: `_record_attempt` swallows all exceptions without any logging or error counter.
  Impact: Stats persistence failures become silent data loss; operators cannot detect missing attempt records or diagnose store issues.
  Recommendation: Log a structured error event including correlation fields and the store error, or surface a metric/counter for record failures.
  Architecture alignment: No

- Severity: High
  File: src/chaos/domain/block.py
  Issue: No log/telemetry events are emitted for `block_start`, `block_success`, `block_failure`, or recovery policy attempts despite the observability vocabulary in the architecture.
  Impact: There is no event stream to debug execution flow, recovery decisions, or failures, making traces and incident response nearly impossible.
  Recommendation: Emit structured events at block start/end and around each recovery policy attempt with required correlation fields (`trace_id`, `run_id`, `span_id`, `parent_span_id`, `block_name`, `node_name`, `attempt`, `reason`).
  Architecture alignment: No
