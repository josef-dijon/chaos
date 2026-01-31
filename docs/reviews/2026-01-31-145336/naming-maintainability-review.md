# Naming and Maintainability Review

Timestamp: 2026-01-31-145336

- Severity: Low
  File: src/chaos/domain/block.py
  Issue: `current_request` is never updated inside `_execute_graph`, so the name implies per-node evolution that does not exist.
  Impact: Misleading names obscure the data flow and make it harder to reason about whether requests are transformed between nodes.
  Recommendation: Rename `current_request` to `base_request` or update the variable when a node response should drive the next request.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/messages.py
  Issue: `Request.payload` is typed as `Dict[str, Any]`, but callers (e.g., LLMPrimitive) treat it as `str | dict` and raise on non-string values.
  Impact: Type hints mislead maintainers and API consumers, increasing misuse and forcing runtime errors instead of guiding correct usage.
  Recommendation: Update the type to `str | Dict[str, Any]` (or `Any` with explicit docstring constraints) and align docstrings with actual accepted shapes.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/messages.py
  Issue: Response uses the field name `ok` with alias `success`, but the rest of the codebase calls `success()` or passes `success=True/False`.
  Impact: Two names for the same concept reduce readability and make JSON payloads and code usage inconsistent to scan.
  Recommendation: Rename the field to `success` and remove `ok`, or standardize on `success` while keeping `ok` only for backward-compatible serialization.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: The identifier `manager_id` is introduced without a clear domain meaning and is used like a request/span identifier.
  Impact: Unclear naming makes logs and metadata difficult to interpret and causes confusion about who/what is “managing.”
  Recommendation: Rename to a precise term like `request_id`, `execution_id`, or `llm_trace_id` and align docstrings/metadata keys accordingly.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/llm/model_selector.py
  Issue: `ModelSelector.select_model` ignores `request` and always returns `default_model`, despite the class name implying selection logic.
  Impact: The API advertises configurability that does not exist, which misleads maintainers and hides where model routing should live.
  Recommendation: Either implement actual selection logic (e.g., from request metadata) or rename the class/method to `DefaultModelResolver` to reflect reality.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/stats/estimate_builder.py
  Issue: `build_estimate_from_records` accepts a `request` parameter but immediately discards it (`del request`).
  Impact: Dead parameters make the API misleading and invite future callers to believe request-specific estimation exists when it does not.
  Recommendation: Remove the parameter until it is used, or implement request-aware estimation and document what request fields influence the estimate.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/policy.py
  Issue: `RetryPolicy.max_attempts` reads like a total-attempts cap, but the recovery loop treats it as “number of retries after the first attempt.”
  Impact: The name obscures real behavior and makes off-by-one errors easy when configuring retries or reading logs.
  Recommendation: Rename to `max_retries` (or adjust the loop to include the initial attempt) and update docstrings to match.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/llm/llm_request.py
  Issue: `manager_id` is a top-level field and also injected into `metadata`, duplicating a vague concept in two places.
  Impact: Redundant, unclear identifiers make request tracing and auditing harder to follow and increase the chance of divergence.
  Recommendation: Keep a single, clearly named identifier (e.g., `request_id`) and eliminate the duplicate metadata key.
  Architecture alignment: Unknown

- Severity: Low
  File: docs/architecture/core/block-interface.md
  Issue: The doc states there is “no separate concept of manager,” yet runtime metadata introduces `manager_id` for LLM executions.
  Impact: Terminology drift makes the architecture harder to follow and undermines shared vocabulary for maintainers.
  Recommendation: Align terminology by renaming `manager_id` in code/docs or explicitly define what “manager” means in architecture docs.
  Architecture alignment: No

- Severity: Low
  File: docs/architecture/core/block-responses.md
  Issue: The doc specifies a `success` field, while the concrete model exposes `ok` with an alias for `success`.
  Impact: Readers may search for a `success` attribute in code and miss the alias, slowing onboarding and increasing confusion.
  Recommendation: Align the docs with the concrete field name or rename the field to `success` in the model.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: Internal retry metadata uses `llm_attempt` and `block_attempt` keys, but the architecture recommends namespaced keys like `llm.attempt` for internal counters.
  Impact: Non-namespaced keys increase collision risk and make metadata harder to scan in logs.
  Recommendation: Rename internal counters to a namespaced form (`llm.attempt`, `llm.retry_count`) and align with the metadata conventions doc.
  Architecture alignment: Unknown

- Severity: Medium
  File: docs/architecture/core/02-llm-primitive.md
  Issue: The doc defines `payload` as a `str`, but the implementation accepts dict payloads with keys like `prompt`, `content`, or `input`.
  Impact: API consumers and maintainers get conflicting guidance on required inputs, causing avoidable errors and unclear validation behavior.
  Recommendation: Update the doc to reflect the accepted payload shapes or tighten the implementation to enforce string-only payloads.
  Architecture alignment: No

- Severity: Low
  File: src/chaos/domain/block.py
  Issue: Composite terminal responses add metadata keys `source` and `composite`, but `source` is overly generic and its meaning is unclear.
  Impact: Generic metadata keys are easy to misinterpret or collide with application-level metadata.
  Recommendation: Rename to explicit keys like `source_node` and `composite_name`, and document them in the metadata conventions.
  Architecture alignment: Unknown

- Severity: Low
  File: docs/llm-primitive-refined.md
  Issue: The document repeatedly centers “Manager” and `manager_id` terminology, which conflicts with the core architecture’s “everything is a Block; no manager” language.
  Impact: Mixed vocabulary increases cognitive load and makes it unclear which concepts are current vs legacy.
  Recommendation: Either mark this document as legacy and align terms to Blocks, or update the core docs to explicitly define the Manager concept.
  Architecture alignment: No

- Severity: Low
  File: docs/llm-primitive-refined-notes.md
  Issue: Uses Manager/`manager_id` terminology and layered ownership chain that conflicts with the core Block-only vocabulary.
  Impact: Maintainers reading both docs will struggle to reconcile responsibilities and naming, especially for audit metadata.
  Recommendation: Reconcile terminology with the block architecture (or explicitly label this as a legacy sketch).
  Architecture alignment: No

- Severity: Medium
  File: docs/dev/llm-primitive-block-audit.md
  Issue: The audit claims `LLMPrimitive.get_policy_stack` returns a `RepairPolicy` and references internal semantic repair loops, but the current implementation only returns `BubblePolicy` and has no repair loop.
  Impact: Review artifacts drift from reality, confusing maintainers and making it hard to trust the audit as a source of truth.
  Recommendation: Update the audit to reflect current behavior or explicitly label it as historical and out-of-date.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/llm/llm_service.py
  Issue: `_render_prompts` returns a variable named `user_prompt` even when it may include concatenated assistant/system role text.
  Impact: Misleading naming obscures what is actually sent to the model and complicates debugging prompt formatting.
  Recommendation: Rename to `rendered_prompt` or `conversation_prompt` to reflect multi-role content.
  Architecture alignment: Unknown
