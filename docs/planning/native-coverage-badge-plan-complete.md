# Native Coverage Badge Plan

## Goal
Replace the Codecov-based coverage reporting with a simple native GitHub Actions workflow status badge. This badge will reflect whether the coverage checks (strict 95% threshold) passed or failed.

## Implementation Steps
1.  **Modify Workflow:** Update `.github/workflows/coverage.yml` to remove the Codecov upload step and unnecessary permissions.
2.  **Update README:** Replace the Codecov badge with the GitHub Actions workflow status badge.
3.  **Verification:** Commit changes and ensure the workflow runs correctly.

## Verification
-   `uv run pytest` runs locally with coverage.
-   CI workflow syntax is valid.
