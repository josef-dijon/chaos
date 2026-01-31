# Documentation Review
Timestamp: 2026-01-31 15:41:39

## Review Description
LLM Primitive system.

## Scope Summary
- Code: `src/chaos/domain/llm_primitive.py`, `src/chaos/domain/block.py`, `src/chaos/domain/block_estimate.py`, `src/chaos/domain/messages.py`, `src/chaos/domain/policy.py`, `src/chaos/domain/exceptions.py`, `src/chaos/llm/llm_service.py`, `src/chaos/llm/llm_executor.py`, `src/chaos/llm/llm_request.py`, `src/chaos/llm/llm_response.py`, `src/chaos/llm/response_status.py`, `src/chaos/llm/model_selector.py`, `src/chaos/llm/llm_error_mapper.py`, `src/chaos/llm/litellm_stats_adapter.py`, `src/chaos/stats/store_registry.py`, `src/chaos/stats/block_stats_store.py`, `src/chaos/stats/json_block_stats_store.py`, `src/chaos/stats/block_attempt_record.py`, `src/chaos/stats/block_stats_identity.py`, `src/chaos/stats/estimate_builder.py`, `src/chaos/stats/statistics.py`, `src/chaos/config.py`, `scripts/llm_primitive_demo.py`
- Tests: `tests/domain/test_llm_primitive.py`, `tests/llm/test_llm_service.py`, `tests/llm/test_model_selector.py`, `tests/stats/test_block_estimation.py`, `tests/test_config.py`
- Docs: `docs/architecture/core/02-llm-primitive.md`, `docs/architecture/core/block-glossary.md`, `docs/architecture/core/block-interface.md`, `docs/architecture/core/block-responses.md`, `docs/architecture/core/recovery-policy-system.md`, `docs/architecture/core/block-estimation.md`, `docs/architecture/core/block-request-metadata.md`
- Config: `pyproject.toml`

- Severity: Medium
  File: docs/architecture/core/block-request-metadata.md
  Issue: The doc says `payload` is "any", but `Request.payload` is typed as `Dict[str, Any]` and rejects string payloads.
  Impact: Readers will follow the doc and send raw string payloads, which fail validation before `LLMPrimitive` can coerce them.
  Recommendation: Update the doc to reflect `payload` is a dict envelope (or document the accepted keys), or update `Request` to allow `Any` if strings are truly supported.
  Architecture alignment: No

- Severity: Medium
  File: docs/architecture/core/02-llm-primitive.md
  Issue: The Inputs table claims `payload` is a `str`, but `Request.payload` is a dict and LLMPrimitive tests only use dict envelopes.
  Impact: Documentation encourages an input shape that the runtime rejects, causing validation errors before execution.
  Recommendation: Update the Inputs table to describe the dict envelope (`prompt`/`content`/`input`) or revise the Request model to accept raw strings.
  Architecture alignment: No

- Severity: Low
  File: docs/architecture/core/02-llm-primitive.md
  Issue: The policy section states PydanticAI manages API retries, but API retries are actually handled by the OpenAI SDK `max_retries` in `LLMService`.
  Impact: Readers debugging retry behavior will look in the wrong layer and misconfigure retry expectations.
  Recommendation: Clarify that output validation retries are in PydanticAI and API retries come from the OpenAI SDK client configuration.
  Architecture alignment: No

- Severity: Medium
  File: docs/architecture/core/block-request-metadata.md
  Issue: The propagation rules require generating a new `id` for child requests, but `Block._build_child_request` never sets an `id` and `Request` does not auto-generate one.
  Impact: Implementers relying on the documented `id` correlation will not see it in runtime metadata, breaking traceability guarantees.
  Recommendation: Either document that `id` is response-only today or update the implementation to set `metadata["id"]` on requests per the spec.
  Architecture alignment: No

- Severity: Low
  File: docs/architecture/core/block-request-metadata.md
  Issue: The doc mandates callers "MUST" prune child `context`, but `Block._build_child_request` forwards the full parent context unchanged.
  Impact: The documented context-minimization guarantee is not true in the default implementation, which can lead to over-sharing and heavier payloads.
  Recommendation: Update the spec to mark pruning as a caller responsibility (not enforced by the base class), or implement actual pruning hooks in the base class.
  Architecture alignment: No

- Severity: Medium
  File: docs/architecture/core/block-interface.md
  Issue: The document states block state is used to guard execution and prevent re-entrancy, but `Block.execute` does not check or enforce state before running.
  Impact: The contract implies safety that the implementation does not provide, which can mislead callers about concurrency guarantees.
  Recommendation: Either document that state is informational-only today or add explicit guard logic in `Block.execute` and update docs accordingly.
  Architecture alignment: No

- Severity: Low
  File: docs/architecture/core/block-request-metadata.md
  Issue: The doc recommends namespaced internal retry counters (e.g., `"llm.retry_count"`), but `LLMPrimitive` emits `llm_calls`/`llm_retry_count` and `llm_attempt` without a namespace.
  Impact: Users following the doc will search for namespaced keys and miss the actual metadata fields in responses and stats.
  Recommendation: Either update the doc to list the current keys or rename emitted metadata keys to the recommended namespace format.
  Architecture alignment: No

- Severity: Medium
  File: docs/architecture/core/02-llm-primitive.md
  Issue: The configuration surface omits runtime-relevant constructor options like `output_retries`, `config`, `stats_adapter`, `llm_service`, and `model_selector` that change behavior.
  Impact: Developers can unknowingly miss important tuning knobs or assume the primitive is less configurable than it is.
  Recommendation: Expand the configuration table to include these parameters or explicitly document them as internal/testing hooks.
  Architecture alignment: No

- Severity: Low
  File: docs/architecture/core/02-llm-primitive.md
  Issue: The implementation note states provider calls are routed through LiteLLM, but `Config.litellm_use_proxy` can disable proxy routing entirely.
  Impact: Operational docs are misleading for direct-to-provider deployments and can cause misconfigured routing expectations.
  Recommendation: Update the note to say routing is conditional on `litellm_use_proxy` and document the fallback path.
  Architecture alignment: No

- Severity: Medium
  File: docs/architecture/core/02-llm-primitive.md
  Issue: The recovery section says local non-LLM errors (e.g., invalid payload) still use the recovery policy system, but `LLMPrimitive.get_policy_stack` always returns only `BubblePolicy`.
  Impact: Readers will expect recovery policies to apply to invalid payloads, but the implementation will always bubble without recovery.
  Recommendation: Either document that LLMPrimitive always bubbles (including invalid payloads) or implement a distinct policy stack for local errors.
  Architecture alignment: No

- Severity: Low
  File: docs/architecture/core/block-request-metadata.md
  Issue: The reserved key table specifies `duration_ms` as an int, but `Block.execute` records it as a float.
  Impact: Consumers relying on integer duration values may mis-handle the data or fail strict schema validation.
  Recommendation: Update the doc to allow float milliseconds or cast duration to int in code and document the rounding behavior.
  Architecture alignment: No
