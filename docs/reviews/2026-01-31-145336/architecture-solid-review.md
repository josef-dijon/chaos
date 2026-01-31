# Architecture and SOLID Review

Timestamp: 2026-01-31-145336

- Severity: Medium
  File: src/chaos/domain/messages.py
  Issue: `Request.payload` is typed as `Dict[str, Any]`, but the architecture contract defines `payload` as `any` and LLMPrimitive expects string payloads; the request envelope is over-constrained.
  Impact: Blocks that legitimately accept non-dict payloads are forced into dict wrappers or rejected by validation, undermining the core Block interface and creating cross-layer coupling.
  Recommendation: Change `Request.payload` to `Any` (or a permissive union) and update any schema/validation assumptions so payload shape is block-specific.
  Architecture alignment: No

- Severity: High
  File: src/chaos/domain/block.py
  Issue: RepairPolicy flow discards the repaired `Request` by rebuilding from the parent request and only copying payload/context, violating the rule that repair must return a new request envelope.
  Impact: Repair functions cannot update metadata or request-level fields; recovery can silently ignore critical changes and violate deterministic repair semantics.
  Recommendation: Use the `repaired` request directly when building the next child attempt (preserving its metadata) and avoid reconstructing from the parent request.
  Architecture alignment: No

- Severity: High
  File: src/chaos/domain/block.py
  Issue: Composite execution returns the child `Response` directly on failure, so the response metadata (block_name/span_id/attempt) reflects the child, not the composite boundary.
  Impact: The composite boundary leaks child identity, breaking traceability, response ownership, and the architecture’s requirement that each block returns its own outcome envelope.
  Recommendation: Synthesize a composite-level failure response (or clone and re-stamp metadata) so the returned response reflects the composite block as the responder.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Child request construction does not generate a new `metadata.id` despite the architecture’s requirement to create a new envelope id per request.
  Impact: Requests and responses cannot be uniquely correlated across nested executions, undermining observability and ledger provenance.
  Recommendation: Generate and set a new `metadata.id` when building child requests (and optionally for the root request in `_with_base_metadata`).
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Child request construction clones the parent `context` wholesale; the base composite logic does not prune or map context for the child.
  Impact: Violates the request contract (caller must minimize context), increases coupling between blocks, and creates hidden dependencies across boundaries.
  Recommendation: Introduce a required hook or override to prune/map `context` per child, or enforce explicit context mapping in composite definitions.
  Architecture alignment: No

- Severity: Low
  File: src/chaos/domain/block.py
  Issue: RetryPolicy execution ignores `delay_seconds` and does not implement any backoff or jitter behavior.
  Impact: Recovery behavior diverges from the recovery policy contract and can overwhelm downstream systems during retries.
  Recommendation: Honor `delay_seconds` (and optional jitter if added) before retry attempts, or delegate retry handling to a policy handler that enforces delays.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Domain `Block` directly depends on engine registries/handlers (`ConditionRegistry`, `RepairRegistry`, `PolicyHandler`), mixing orchestration infrastructure into the core domain model.
  Impact: Creates tight coupling across layers, makes domain blocks harder to test in isolation, and violates clean boundaries by requiring engine-level singletons inside core execution logic.
  Recommendation: Introduce domain-level abstractions or dependency injection for condition resolution and recovery handling, keeping engine-specific registries in the outer layer.
  Architecture alignment: No

- Severity: Low
  File: src/chaos/domain/llm_primitive.py
  Issue: Internal attempt metadata uses non-namespaced keys (`block_attempt`, `llm_attempt`) instead of the recommended namespaced convention for internal retries.
  Impact: Increases the risk of metadata collisions and makes observability contracts harder to evolve without breaking consumers.
  Recommendation: Rename internal counters to a namespaced form (for example `llm.attempt`, `llm.retry_count`, `block.attempt`) and document them.
  Architecture alignment: No

- Severity: Medium
  File: src/chaos/domain/block.py
  Issue: Condition resolution is validated at execution time, not during graph construction, even though the architecture requires fail-fast validation during build.
  Impact: Invalid graphs can be instantiated and only fail at runtime, violating deterministic construction guarantees and making errors harder to detect.
  Recommendation: Move condition validation into `build()`/`set_graph()` or add an explicit validation step during construction.
  Architecture alignment: No

- Severity: Low
  File: tests/domain/test_llm_primitive.py
  Issue: Tests do not assert required observability metadata (`trace_id`, `span_id`, `block_name`, `attempt`) despite explicit architecture testing guidelines.
  Impact: Metadata regressions can slip into production, breaking traceability and recovery analytics.
  Recommendation: Add assertions for the minimum response metadata keys and ensure they are correctly propagated in LLMPrimitive tests.
  Architecture alignment: No
