# Performance Scalability Review
Timestamp: 2026-01-31 15:41:39

## Review Description
LLM Primitive system.

## Scope Summary
- Code: `src/chaos/domain/llm_primitive.py`, `src/chaos/domain/block.py`, `src/chaos/domain/block_estimate.py`, `src/chaos/domain/messages.py`, `src/chaos/domain/policy.py`, `src/chaos/domain/exceptions.py`, `src/chaos/llm/llm_service.py`, `src/chaos/llm/llm_executor.py`, `src/chaos/llm/llm_request.py`, `src/chaos/llm/llm_response.py`, `src/chaos/llm/response_status.py`, `src/chaos/llm/model_selector.py`, `src/chaos/llm/llm_error_mapper.py`, `src/chaos/llm/litellm_stats_adapter.py`, `src/chaos/stats/store_registry.py`, `src/chaos/stats/block_stats_store.py`, `src/chaos/stats/json_block_stats_store.py`, `src/chaos/stats/block_attempt_record.py`, `src/chaos/stats/block_stats_identity.py`, `src/chaos/stats/estimate_builder.py`, `src/chaos/stats/statistics.py`, `src/chaos/config.py`, `scripts/llm_primitive_demo.py`
- Tests: `tests/domain/test_llm_primitive.py`, `tests/llm/test_llm_service.py`, `tests/llm/test_model_selector.py`, `tests/stats/test_block_estimation.py`, `tests/test_config.py`
- Docs: `docs/architecture/core/02-llm-primitive.md`, `docs/architecture/core/block-glossary.md`, `docs/architecture/core/block-interface.md`, `docs/architecture/core/block-responses.md`, `docs/architecture/core/recovery-policy-system.md`, `docs/architecture/core/block-estimation.md`, `docs/architecture/core/block-request-metadata.md`
- Config: `pyproject.toml`

- Severity: Medium
  File: `src/chaos/domain/block.py`
  Issue: `_execute_graph` calls `_validate_graph` on every execution, re-walking nodes/transitions for a graph that is effectively static after `build()`.
  Impact: Adds O(nodes + transitions) overhead per request and scales poorly for large composite graphs or high QPS.
  Recommendation: Validate once during `build()`/`set_graph()` and cache a validated flag; only revalidate when graph config changes.
  Architecture alignment: Yes

- Severity: Medium
  File: `src/chaos/domain/block.py`
  Issue: `_with_base_metadata` and `_build_child_request` use `model_copy(deep=True)` for every step/retry, cloning full payload/context even when unchanged.
  Impact: Deep copies amplify memory use and CPU time on large payloads and increase latency with nested composites and retries.
  Recommendation: Prefer shallow copies with targeted metadata mutation (or immutable metadata struct) and only deep-copy payload/context when mutation is required.
  Architecture alignment: Unknown

- Severity: Medium
  File: `src/chaos/llm/llm_service.py`
  Issue: `_build_model` constructs a new `AsyncOpenAI` client and `OpenAIChatModel` on every request with no reuse or pooling.
  Impact: Repeated client/model instantiation increases latency and connection churn under high QPS, and prevents efficient connection reuse.
  Recommendation: Cache `OpenAIChatModel`/provider by (model, api_base, api_key, retries) or inject a long-lived client via `model_builder` for reuse.
  Architecture alignment: Unknown

- Severity: High
  File: `src/chaos/stats/json_block_stats_store.py`
  Issue: `record_attempt` rewrites the full JSON file on every attempt via `_save`, and `_save` serializes the entire in-memory list each time.
  Impact: O(n) disk I/O per attempt causes severe latency spikes and poor throughput as history grows; can become a bottleneck on busy systems.
  Recommendation: Switch to append-only journaling or a real datastore; at minimum batch writes, rotate files, or checkpoint periodically instead of per attempt.
  Architecture alignment: Unknown

- Severity: Medium
  File: `src/chaos/stats/json_block_stats_store.py`
  Issue: `estimate` linearly scans all stored records to filter by block identity on every call.
  Impact: O(n) CPU time per estimate increases latency as attempt history grows and scales poorly with many blocks.
  Recommendation: Maintain an index keyed by (block_name, block_type, version) or pre-group records when loading to make estimates O(k) for relevant samples.
  Architecture alignment: Unknown

- Severity: Medium
  File: `src/chaos/stats/json_block_stats_store.py`
  Issue: `_load` reads the entire JSON file into memory and keeps all records resident for the lifetime of the process.
  Impact: Memory usage grows unbounded with historical attempts and can degrade performance or crash long-lived services.
  Recommendation: Use a bounded store (rolling window), streaming/append-only format with paging, or a database with query limits.
  Architecture alignment: Unknown

- Severity: Low
  File: `src/chaos/domain/block.py`
  Issue: `_execute_graph` resolves `ConditionRegistry.get` for each transition branch on every execution instead of pre-resolving conditions.
  Impact: Adds repeated registry lookups on hot paths and increases latency with many branching transitions.
  Recommendation: Resolve condition callables once during graph setup and store them in the transition config for direct invocation.
  Architecture alignment: Unknown

- Severity: Low
  File: `src/chaos/llm/llm_service.py`
  Issue: `_run_agent` creates a new PydanticAI `Agent` for every request, even when model/output schema are identical.
  Impact: Per-request object construction adds overhead and GC pressure for high-throughput workloads.
  Recommendation: Cache agents keyed by (model, output schema, system prompt) or introduce a lightweight agent factory with reuse.
  Architecture alignment: Unknown

- Severity: Medium
  File: `src/chaos/domain/block.py`
  Issue: `RetryPolicy.delay_seconds` is never honored in `_execute_child_with_recovery`, resulting in tight retry loops.
  Impact: Burst retries can overwhelm upstream providers, increase rate-limit errors, and amplify latency spikes under load.
  Recommendation: Implement backoff/sleep using `delay_seconds` (and consider jitter/exponential backoff) before each retry attempt.
  Architecture alignment: Yes

- Severity: Low
  File: `src/chaos/stats/statistics.py`
  Issue: `mean_std` materializes the entire iterable into a list and makes multiple passes over the data.
  Impact: Extra memory and CPU overhead for large sample sets, which compounds when estimates are recalculated frequently.
  Recommendation: Use a single-pass streaming algorithm (e.g., Welford) or accept iterables already materialized to avoid extra copies.
  Architecture alignment: Not Available

- Severity: Low
  File: `src/chaos/domain/block.py`
  Issue: `_execute_graph` deep-copies the terminal `Response` just to add metadata (`response.model_copy(deep=True)`), even when the payload is large.
  Impact: Unnecessary memory churn and latency when responses contain big data structures.
  Recommendation: Avoid deep copy by cloning only metadata or creating a shallow copy with updated metadata.
  Architecture alignment: Unknown
