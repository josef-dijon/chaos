# Documentation Review

Timestamp: 2026-01-31-145336

- Severity: High
  File: docs/architecture/core/block-observability.md
  Issue: Documentation requires responses to include trace/span/attempt metadata, but composite success responses drop these fields and only include `source/composite/last_node`.
  Impact: Readers will assume traceability is preserved across composite boundaries, but actual behavior loses correlation fields, making observability and recovery analysis unreliable.
  Recommendation: Update docs to note the current composite response metadata loss or (preferred) document the actual behavior and explicitly mark it as a gap requiring implementation.
  Architecture alignment: No

- Severity: Medium
  File: docs/architecture/core/02-llm-primitive.md
  Issue: Input contract says `payload` is a string, but the implementation accepts either a string or a dict containing `prompt`, `content`, or `input` keys.
  Impact: Callers relying on the docs may pass only strings and miss supported dict shapes; conversely, callers may pass dict payloads that are not documented and later removed as “unsupported.”
  Recommendation: Document the accepted dict payload shapes (or explicitly deprecate them and enforce string-only in code).
  Architecture alignment: Unknown

- Severity: Medium
  File: docs/architecture/core/02-llm-primitive.md
  Issue: The doc claims provider calls are “routed through LiteLLM” and schema hints are passed to providers, but the implementation uses PydanticAI with the OpenAI SDK and only optionally points at a proxy base URL.
  Impact: Readers will expect LiteLLM client behavior, proxy-only metadata, and response-format features that are not implemented, which can lead to incorrect operational setups.
  Recommendation: Update the implementation note to describe the actual stack (PydanticAI + OpenAI SDK with optional LiteLLM-compatible proxy) and clarify how schema enforcement is performed.
  Architecture alignment: No

- Severity: Low
  File: docs/architecture/core/02-llm-primitive.md
  Issue: Failure modes list only schema/rate limit/api key/context length errors, but the LLM layer also emits generic `llm_execution_failed` and other mapped reasons.
  Impact: Operators will not know about non-classified failures, which makes debugging and recovery policy planning incomplete.
  Recommendation: Add a “generic/unknown LLM failure” reason and describe how it is classified when error types fall outside the known set.
  Architecture alignment: Unknown

- Severity: Low
  File: docs/architecture/core/block-request-metadata.md
  Issue: Propagation rules say composites should generate a new `id` for child requests, but `Request` has no auto-id and `_build_child_request` does not set it.
  Impact: Anyone relying on `id` for request-level tracing will not see it on child requests, despite docs implying it exists.
  Recommendation: Either implement `id` generation in child request construction or soften the doc to mark `id` as optional and not currently emitted.
  Architecture alignment: Unknown

- Severity: Low
  File: docs/architecture/core/block-execution-semantics.md
  Issue: Child request construction requires context pruning, but the composite implementation clones the full parent context unchanged.
  Impact: Readers will assume context minimization is enforced; in practice, sensitive or bloated context may be passed to children without warning.
  Recommendation: Document the current behavior (no automatic pruning) and move the pruning requirement to a “caller responsibility” note if it is not enforced.
  Architecture alignment: Unknown

- Severity: Medium
  File: docs/llm-primitive-refined.md
  Issue: The dependency stack and runtime layering describe instructor/tenacity/LiteLLM + StableTransport/Manager layers that do not exist in the current implementation, which instead uses PydanticAI + OpenAI SDK.
  Impact: New contributors will attempt to configure or debug non-existent layers and packages, slowing onboarding and leading to incorrect operational assumptions.
  Recommendation: Mark this document as historical or replace the stack description with the current PydanticAI-based pipeline.
  Architecture alignment: No

- Severity: Medium
  File: docs/llm-primitive-refined.md
  Issue: The documented LLMRequest/LLMResponse shapes include fields like `budget`, `tag`, `history`, `manager_id`, and cost/time estimates, but the implemented `LLMRequest`/`LLMResponse` types do not define these fields.
  Impact: Consumers may build integrations around fields that do not exist, causing runtime failures or incorrect assumptions about budgeting and audit data.
  Recommendation: Update the schema examples to match `src/chaos/llm/llm_request.py` and `src/chaos/llm/llm_response.py`, or explicitly label them as hypothetical future fields.
  Architecture alignment: No

- Severity: Low
  File: docs/llm-primitive-refined-notes.md
  Issue: The layering notes assert a Manager/StableTransport/ModelStatsService stack and budgeting-based model selection that are not implemented in the current codebase.
  Impact: The notes read like actionable guidance but describe components that do not exist, which can misdirect architectural work.
  Recommendation: Add a prominent “concept-only” disclaimer and a pointer to current implementation files, or move this into an archive folder.
  Architecture alignment: No

- Severity: Low
  File: docs/architecture/core/block-recovery-semantics.md
  Issue: The doc says callers should map from `reason` when `error_type` is missing after serialization, but the implementation defaults to `Exception` and does not perform any reason-based mapping.
  Impact: Readers will assume reason-based fallback exists and design workflows around it, but actual runtime behavior will collapse diverse failures into a single recovery path.
  Recommendation: Either implement the reason-based fallback mapping or clarify in the doc that it is aspirational and not implemented.
  Architecture alignment: Unknown

- Severity: Medium
  File: docs/architecture/core/block-request-metadata.md
  Issue: The request contract states `payload` can be any type, but the `Request` model enforces `payload: Dict[str, Any]` and will not accept non-dict payloads without coercion.
  Impact: Documentation implies string payloads are supported for all blocks, but actual request validation can reject them, leading to runtime errors.
  Recommendation: Update the doc to match the concrete `Request` schema or loosen the schema to accept arbitrary payload types.
  Architecture alignment: Unknown

- Severity: Medium
  File: docs/dev/llm-primitive-block-audit.md
  Issue: The audit claims `LLMPrimitive.get_policy_stack` returns a `RepairPolicy(add_validation_feedback)`, but the current implementation returns `BubblePolicy()` only.
  Impact: The audit’s “critical” finding about a missing repair function is no longer accurate, which undermines confidence in the rest of the audit.
  Recommendation: Refresh the audit findings or mark this section as stale with the commit/date when behavior changed.
  Architecture alignment: Not Available
