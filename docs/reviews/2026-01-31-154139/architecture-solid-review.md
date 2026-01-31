# Architecture Solid Review
Timestamp: 2026-01-31 15:41:39

## Review Description
LLM Primitive system.

## Scope Summary
- Code: `src/chaos/domain/llm_primitive.py`, `src/chaos/domain/block.py`, `src/chaos/domain/block_estimate.py`, `src/chaos/domain/messages.py`, `src/chaos/domain/policy.py`, `src/chaos/domain/exceptions.py`, `src/chaos/llm/llm_service.py`, `src/chaos/llm/llm_executor.py`, `src/chaos/llm/llm_request.py`, `src/chaos/llm/llm_response.py`, `src/chaos/llm/response_status.py`, `src/chaos/llm/model_selector.py`, `src/chaos/llm/llm_error_mapper.py`, `src/chaos/llm/litellm_stats_adapter.py`, `src/chaos/stats/store_registry.py`, `src/chaos/stats/block_stats_store.py`, `src/chaos/stats/json_block_stats_store.py`, `src/chaos/stats/block_attempt_record.py`, `src/chaos/stats/block_stats_identity.py`, `src/chaos/stats/estimate_builder.py`, `src/chaos/stats/statistics.py`, `src/chaos/config.py`, `scripts/llm_primitive_demo.py`
- Tests: `tests/domain/test_llm_primitive.py`, `tests/llm/test_llm_service.py`, `tests/llm/test_model_selector.py`, `tests/stats/test_block_estimation.py`, `tests/test_config.py`
- Docs: `docs/architecture/core/02-llm-primitive.md`, `docs/architecture/core/block-glossary.md`, `docs/architecture/core/block-interface.md`, `docs/architecture/core/block-responses.md`, `docs/architecture/core/recovery-policy-system.md`, `docs/architecture/core/block-estimation.md`, `docs/architecture/core/block-request-metadata.md`
- Config: `pyproject.toml`

- Severity: Medium
  File: src/chaos/domain/messages.py
  Issue: Request.payload is typed as Dict[str, Any], which contradicts the architecture contract that payload can be any type (strings, objects, etc.).
  Impact: This constrains callers and blocks that legitimately accept non-dict payloads, forcing coercions or silent schema drift away from the documented block contract.
  Recommendation: Change Request.payload to Any (or a union that includes str) and update validation/tests to preserve the architecture's payload flexibility.
  Architecture alignment: No

- Severity: High
  File: src/chaos/domain/block.py
  Issue: Composite responses retain child correlation metadata because _attach_correlation_metadata uses setdefault, so child span/attempt IDs remain instead of the composite's own attempt identifiers.
  Impact: Observability and recovery tracing become ambiguous; composite-level attempts cannot be reliably distinguished from child attempts, violating the request/metadata propagation rules.
  Recommendation: When a composite returns a synthesized response, explicitly overwrite trace/span/run/attempt/block_name in response.metadata with the composite's request metadata (not setdefault).
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Several failure responses omit error_type (e.g., unknown_node in _execute_graph), despite error_type being the canonical selector for recovery policies.
  Impact: Callers cannot consistently select recovery policies, and failures become less deterministic across the block boundary.
  Recommendation: Set error_type on all Response failures, using a stable error classification (or Exception as a default) per the response contract.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/messages.py
  Issue: Request objects never receive a unique metadata id, and _build_child_request does not generate one, despite the request/metadata spec recommending per-envelope ids.
  Impact: Request/response correlation breaks at the request layer; tracing and recovery replay cannot reliably identify individual request envelopes.
  Recommendation: Generate a metadata "id" in Request.__init__ or in Block._with_base_metadata and Block._build_child_request to ensure each request has a unique envelope id.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Domain-level Block depends directly on engine registries (ConditionRegistry, RepairRegistry, PolicyHandler), coupling core domain primitives to orchestration/infrastructure modules.
  Impact: Breaks clean layering and makes the domain block untestable without engine wiring, violating dependency inversion and impeding reuse of Block in other runtimes.
  Recommendation: Invert these dependencies via interfaces injected at construction or move orchestration concerns into an engine-layer composite executor.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/llm_primitive.py
  Issue: LLMPrimitive constructs Config and LiteLLMStatsAdapter via global defaults, baking infrastructure configuration and persistence into a domain block.
  Impact: Violates dependency inversion and makes the core block lifecycle dependent on environment/file I/O, reducing portability and test isolation.
  Recommendation: Require Config and stats adapter as injected dependencies (or factory-injected) and keep the block constructor side-effect free.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/llm_primitive.py
  Issue: LLMPrimitive accepts dict payloads with keys like "prompt"/"content", but the architecture contract defines payload as a plain string for LLMPrimitive.
  Impact: Input contract drift makes block usage inconsistent with docs and complicates composition because callers cannot rely on the documented payload shape.
  Recommendation: Enforce a string-only payload or update the architecture doc to explicitly allow the dict shape and required keys.
  Architecture alignment: No

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: Invalid input payloads are classified as SchemaError, conflating input validation failures with output schema failures.
  Impact: Recovery policy selection and analytics cannot distinguish between bad input and model output schema errors.
  Recommendation: Introduce a dedicated input validation error type (or use a generic validation error) and map invalid payloads to that error_type with a distinct reason.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/stats/store_registry.py
  Issue: Default stats store is instantiated at import time using Config.load(), performing configuration and file-system decisions during module import.
  Impact: Hidden side effects at import violate clean boundaries, complicate testing, and make dependency injection harder for domain blocks.
  Recommendation: Lazily initialize the default store on first access or inject it from the application layer.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: Internal retry metadata uses generic keys like "llm_attempt" instead of the recommended namespaced form (e.g., "llm.attempt").
  Impact: Increases risk of metadata key collisions in composites that merge metadata from multiple blocks or tools.
  Recommendation: Namespace internal metadata keys per the request/metadata guidelines and document them.
  Architecture alignment: Yes

- Severity: Low
  File: tests/domain/test_llm_primitive.py
  Issue: Tests never assert the documented payload contract or request metadata requirements (string payloads, unique request ids, propagation rules).
  Impact: Contract drift can ship unnoticed, and architecture compliance becomes a documentation-only check.
  Recommendation: Add tests that cover string payloads and request/response metadata propagation, including request id creation and attempt/spans.
  Architecture alignment: Unknown
