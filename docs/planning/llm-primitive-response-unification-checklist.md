# LLM Primitive + Response Unification Checklist

## Status
Draft

## Contents
- [x] Update architecture docs for unified `Response` model.
- [x] Replace `SuccessResponse`/`FailureResponse` with unified `Response` in domain models.
- [x] Update runtime code to use `Response.success()`.
- [x] Rename `output_schema` -> `output_data_model` in code and tests.
- [x] Pass schema hints to LiteLLM when supported.
- [x] Update harness and scripts for new API.
- [x] Run `uv run pytest` with coverage >= 95%.

## References
- [LLM Primitive + Response Unification Plan](llm-primitive-response-unification-plan.md)
