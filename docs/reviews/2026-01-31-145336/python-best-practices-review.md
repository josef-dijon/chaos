# Python Best Practices Review

Timestamp: 2026-01-31-145336

- Severity: Medium
  File: src/chaos/domain/messages.py
  Issue: `Request.payload` is typed as `Dict[str, Any]` but callers accept strings or other shapes (e.g., `LLMPrimitive._coerce_payload`).
  Impact: Type checkers and readers get a false contract; downstream code may skip validation or narrow incorrectly.
  Recommendation: Widen `payload` to `Any` or a `Union[str, Mapping[str, Any]]` and document the allowed shapes.
  Architecture alignment: Unknown

- Severity: Medium
  File: src/chaos/domain/llm_primitive.py
  Issue: `_coerce_payload` contains a `str` branch, but `Request.payload` is currently a dict-only field, making the string path effectively dead.
  Impact: The implementation and data model disagree, so type narrowing and validation are inconsistent with runtime expectations.
  Recommendation: Align `Request.payload` typing/validation with `_coerce_payload` (or remove the `str` branch) so the contract matches behavior.
  Architecture alignment: Unknown

- Severity: Low
  File: src/chaos/llm/llm_service.py
  Issue: `_run_agent` passes `system_prompt=system_prompt or ()`, which yields an empty tuple instead of `None`/`str` when no system prompt is provided.
  Impact: This violates the annotated type contract and can trigger subtle runtime type errors if the SDK expects a string or None.
  Recommendation: Pass `None` (or an empty string) when no system prompt exists; avoid non-string sentinel values.
  Architecture alignment: Unknown

- Severity: Low
  File: tests/domain/test_llm_primitive.py
  Issue: Many test functions/classes lack docstrings despite the project standard requiring documentation for every function and class.
  Impact: Violates the documented documentation standard and makes test intent harder to scan consistently.
  Recommendation: Add concise docstrings to each test function/class or explicitly exempt tests in the documentation standard.
  Architecture alignment: Yes
