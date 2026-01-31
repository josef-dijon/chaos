# Logging Observability Review
Timestamp: 2026-01-31 15:41:39

## Review Description
LLM Primitive system.

## Scope Summary
- Code: `src/chaos/domain/llm_primitive.py`, `src/chaos/domain/block.py`, `src/chaos/domain/block_estimate.py`, `src/chaos/domain/messages.py`, `src/chaos/domain/policy.py`, `src/chaos/domain/exceptions.py`, `src/chaos/llm/llm_service.py`, `src/chaos/llm/llm_executor.py`, `src/chaos/llm/llm_request.py`, `src/chaos/llm/llm_response.py`, `src/chaos/llm/response_status.py`, `src/chaos/llm/model_selector.py`, `src/chaos/llm/llm_error_mapper.py`, `src/chaos/llm/litellm_stats_adapter.py`, `src/chaos/stats/store_registry.py`, `src/chaos/stats/block_stats_store.py`, `src/chaos/stats/json_block_stats_store.py`, `src/chaos/stats/block_attempt_record.py`, `src/chaos/stats/block_stats_identity.py`, `src/chaos/stats/estimate_builder.py`, `src/chaos/stats/statistics.py`, `src/chaos/config.py`, `scripts/llm_primitive_demo.py`
- Tests: `tests/domain/test_llm_primitive.py`, `tests/llm/test_llm_service.py`, `tests/llm/test_model_selector.py`, `tests/stats/test_block_estimation.py`, `tests/test_config.py`
- Docs: `docs/architecture/core/02-llm-primitive.md`, `docs/architecture/core/block-glossary.md`, `docs/architecture/core/block-interface.md`, `docs/architecture/core/block-responses.md`, `docs/architecture/core/recovery-policy-system.md`, `docs/architecture/core/block-estimation.md`, `docs/architecture/core/block-request-metadata.md`
- Config: `pyproject.toml`

- Severity: Medium
- File: `src/chaos/domain/block.py`
- Issue: `Block._record_attempt` swallows all exceptions from the stats store without emitting any log or error signal.
- Impact: Metrics loss becomes silent, breaking observability for failed or successful attempts and hiding storage outages.
- Recommendation: Log record-attempt failures with trace_id/span_id/block_name and exception details; optionally surface a health metric/counter for stats failures.
- Architecture alignment: Unknown

- Severity: Low
- File: `src/chaos/domain/block.py`
- Issue: Request/child request metadata never sets a new `id` value, despite the architecture propagation rule to generate a unique envelope id per child request.
- Impact: Request envelopes are not uniquely identifiable, making it harder to correlate retries/repairs and nested executions in logs or traces.
- Recommendation: Populate `metadata["id"]` in `_with_base_metadata` and regenerate it in `_build_child_request` for each child attempt.
- Architecture alignment: No

- Severity: Medium
- File: `src/chaos/llm/llm_service.py`
- Issue: `LLMRequest.metadata` (including trace/run/span identifiers) is never propagated to the underlying provider call, so upstream LLM logs cannot be correlated with internal traces.
- Impact: Provider-side observability is blind to request lineage, making incident debugging and cost attribution significantly harder.
- Recommendation: Pass trace/run/span identifiers via provider metadata/tags if supported, or emit a structured log around the provider call with those IDs.
- Architecture alignment: Unknown

- Severity: Low
- File: `src/chaos/domain/llm_primitive.py`
- Issue: Internal attempt counters use non-namespaced keys (`block_attempt`, `llm_attempt`) instead of the namespaced form recommended for internal retry metadata.
- Impact: Metadata keys are more likely to collide with caller-provided fields and make log filters inconsistent across components.
- Recommendation: Rename to namespaced keys like `llm.block_attempt` and `llm.attempt` (or similar) and update downstream usage.
- Architecture alignment: No

- Severity: High
- File: `src/chaos/llm/llm_error_mapper.py`
- Issue: Error details include `str(error)` and `str(__cause__)`, which may embed raw prompts, model outputs, or credentials from upstream exceptions.
- Impact: PII and sensitive data can be persisted in responses/logs and grow without bounds, violating logging hygiene and privacy controls.
- Recommendation: Sanitize error strings (redact tokens, prompts, headers) and cap detail size; prefer stable error codes plus minimal safe fields (e.g., status_code).
- Architecture alignment: Unknown

- Severity: Medium
- File: `src/chaos/domain/block.py`
- Issue: Unhandled exceptions in `Block.execute` are converted to a failure response without any structured log entry.
- Impact: Hard failures vanish from logs and tracing systems, forcing operators to infer outages only from missing stats or downstream errors.
- Recommendation: Emit an error log on exception with `trace_id`, `span_id`, `block_name`, `node_name`, and the exception type/message.
- Architecture alignment: Unknown
