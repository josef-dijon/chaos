# DRY and Dead Code Review

Timestamp: 2026-01-31-145336

- Severity: Medium
- File: src/chaos/stats/json_block_stats_store.py
- Issue: Duplicate record-filtering and estimate-building logic is repeated in src/chaos/stats/in_memory_block_stats_store.py.
- Impact: Any change to filtering criteria or prior/estimate behavior must be updated in two places, inviting drift and inconsistent stats.
- Recommendation: Extract a shared helper (or base class) for filtering relevant records and building the estimate, then call it from both stores.
- Architecture alignment: Unknown

- Severity: Low
- File: src/chaos/llm/llm_error_mapper.py
- Issue: schema_error, rate_limit_error, and api_key_error mappings are duplicated across multiple branches (typed exceptions, httpx status, string heuristics).
- Impact: Any future change to reason/status or error_type must be updated in several branches, increasing inconsistency risk.
- Recommendation: Factor shared mappings into small helper functions or a mapping table to collapse repeated return blocks.
- Architecture alignment: Unknown

- Severity: Low
- File: src/chaos/domain/block.py
- Issue: ConditionRegistry.get is resolved in _validate_graph and again in _execute_graph for the same transitions, duplicating error handling paths.
- Impact: Validation and execution can drift (e.g., different error reasons) and redundant lookup adds noise to the execution loop.
- Recommendation: Cache resolved conditions during validation or centralize condition resolution to a single helper used by both methods.
- Architecture alignment: Unknown

- Severity: Low
- File: src/chaos/llm/model_selector.py
- Issue: select_model is a pass-through that deletes request and always returns the default, making the abstraction a no-op.
- Impact: Extra indirection without behavior increases surface area and can hide the fact that per-request selection is not implemented.
- Recommendation: Either implement real selection logic or inline model choice in LLMPrimitive and remove the unused selector abstraction.
- Architecture alignment: Unknown

- Severity: Low
- File: src/chaos/stats/estimate_builder.py
- Issue: build_estimate_from_records accepts request but immediately deletes it; request is unused in all current estimate flows.
- Impact: Dead parameter suggests incomplete design and adds confusion/noise to every call site.
- Recommendation: Remove the request parameter throughout the estimate path or implement request-aware estimation (e.g., token-based bucketing) to justify it.
- Architecture alignment: Unknown

- Severity: Low
- File: src/chaos/domain/block.py
- Issue: Retry safety checks for RetryPolicy and RepairPolicy are duplicated with identical unsafe_to_retry responses.
- Impact: Any future change to retry eligibility or error messaging must be updated in multiple branches, increasing drift risk.
- Recommendation: Extract a shared helper to validate retry safety and return a standardized failure response used by both branches.
- Architecture alignment: Unknown

- Severity: Low
- File: src/chaos/llm/litellm_stats_adapter.py
- Issue: estimate() re-checks for prior/sample_size==0 even though the underlying store already returns a prior when there is no data.
- Impact: Redundant indirection makes behavior harder to reason about and invites subtle divergence if store logic changes.
- Recommendation: Return the store estimate directly, or move the fallback logic into a single shared layer and remove the duplicate check here.
- Architecture alignment: Unknown

- Severity: Medium
- File: src/chaos/stats/in_memory_block_stats_store.py
- Issue: Duplicate record-filtering and estimate-building logic is repeated in src/chaos/stats/json_block_stats_store.py.
- Impact: Changes to stats selection or estimate behavior can diverge across stores, leading to inconsistent outputs in tests vs production.
- Recommendation: Centralize the common filtering/estimate logic in a shared helper to ensure identical behavior.
- Architecture alignment: Unknown
