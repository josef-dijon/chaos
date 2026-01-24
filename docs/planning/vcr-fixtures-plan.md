# VCR Fixtures Plan

## Purpose
Add deterministic, replayable HTTP fixtures for functional LLM tests so integration coverage can run without live network calls.

## Goals
- Replace the fake LLM in functional tests with recorded OpenAI responses.
- Keep tests deterministic, fast, and isolated from network availability.
- Ensure secrets are never recorded in fixture files.
- Align with `docs/architecture.md` and existing testing standards.

## Non-Goals
- Changing the agent architecture or memory model.
- Replacing unit-test mocks (unit tests will continue to mock LLM calls).

## Constraints
- Use `uv` for running scripts/tests.
- Maintain >=95% coverage and keep tests deterministic.
- Store fixtures under `tests/fixtures/` and avoid committing secrets.

## Plan
### Phase 1: Fixture Infrastructure
1. Add `vcrpy` (and any minimal helpers) to dev dependencies in `pyproject.toml`.
2. Create a shared pytest fixture (e.g., `tests/functional/conftest.py`) that:
   - Configures VCR with a cassette directory (`tests/fixtures/vcr`).
   - Filters API keys and authorization headers.
   - Sets record mode to `none` by default.
3. Document how to (re)record cassettes locally when needed.

### Phase 2: Replace Fake LLM in Functional Tests
1. Remove the `FakeChatOpenAI` monkeypatch for functional tests.
2. Wrap each functional test in a VCR cassette using a fixture or marker.
3. Ensure all functional tests share a stable model name and inputs.

### Phase 3: Validation and Coverage
1. Run `uv run pytest --cov` to confirm deterministic pass.
2. Verify cassette files contain no secrets.
3. Update README/testing docs if new recording steps are required.

## Acceptance Criteria
- Functional tests run without network access and pass deterministically.
- Cassettes are stored in `tests/fixtures/vcr` with filtered secrets.
- Unit tests continue to mock LLM calls; no live network calls in CI.
- Coverage remains >=95%.
