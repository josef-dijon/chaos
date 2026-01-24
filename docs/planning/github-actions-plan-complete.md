# GitHub Actions Implementation Plan

## Goal
Implement a GitHub Action to automatically run tests on every push and pull request to the `main` branch.

## 1. Setup
- Create `.github/workflows` directory.

## 2. Implementation
- **Workflow: `test.yml`**
    - Trigger on push to `main` and all pull requests.
    - Strategy: Run on `ubuntu-latest`.
    - Steps:
        1. Checkout code.
        2. Install `uv`.
        3. Set up Python 3.13.
        4. Install dependencies.
        5. Run tests with coverage reporting.

## 3. Verification
- Validate the YAML syntax.
- Since I cannot trigger the action myself (requires a push to a real GitHub repo), I will ensure the local tests still pass and the configuration is idiomatically correct for `uv`.
