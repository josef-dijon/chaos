# VCR Fixtures Checklist

## Phase 1: Fixture Infrastructure
- [ ] Add `vcrpy` to dev dependencies.
- [ ] Add shared VCR pytest fixture with cassette directory + secret filtering.
- [ ] Document cassette recording steps for maintainers.

## Phase 2: Functional Test Updates
- [ ] Remove fake LLM monkeypatch from functional tests.
- [ ] Wrap each functional test with a VCR cassette.
- [ ] Ensure model name and prompts are stable for replay.

## Phase 3: Validation
- [ ] Run `uv run pytest --cov` and confirm >=95% coverage.
- [ ] Inspect cassettes to confirm secrets are filtered.
- [ ] Update README with any new recording instructions.
