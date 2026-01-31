# Development Guide

This document outlines our development standards, workflows, and architecture choices to ensure high quality, testability, and maintainability.

## Architecture & Source of Truth

The [Architecture Index](docs/architecture/index.md) is the **single source of truth** for this project.

- **Direction of Flow:** Information flows strictly from the Architecture Specification to the Codebase.
- **Updates:** Any architectural changes must first be defined and documented in the specification before implementation begins.
- **Compliance:** All code implementation must strictly adhere to the patterns and structures defined in the architecture documents.

## Documentation Standard

All documentation must follow the project documentation standard:
- [Documentation Standard](docs/documentation-standard.md)

## Project Structure & Tooling

- **Language:** Python (Modern conventions)
- **Package Manager:** `uv`
- **Configuration:** `pyproject.toml`
- **Layout:** Standard Python project structure (`src/`, `docs/`, `tests/`).
- **Type:** Python module (importable by other projects).

## Development Workflow

1.  **Execution:** Always run the project and scripts via `uv`.
2.  **Testing Strategy:**
    - **Tools:** `pytest` and `pytest-cov` (or `pycov`).
    - **Coverage Mandate:** Maintain at least **95% test coverage**.
    - **Testability Driver:** Use the coverage requirement to drive architecture. If code is difficult to test, break it down into smaller chunks, functions, or sub-classes.
    - **LLM Mocking:** For unit tests, always mock LLM calls using `unittest.mock` or `pytest-mock`. Avoid real network calls to ensure tests are fast, deterministic, and free. For integration tests, consider using `vcrpy` to record and replay real interactions.
    - **Pre-Commit:** Always run and fix tests before creating a commit.
3.  **Planning Process:**
    - **Plan Before Code:** Never start implementing features without a plan.
    - **Documents:**
        - Create a planning document in `docs/planning/` with a `-plan.md` suffix.
        - Create a companion checklist file in `docs/planning/` with a `-checklist.md` suffix.
    - **Tracking:** Mark checklist items as done as the plan is executed.
    - **Index Updates:** Keep `docs/planning/index.md` updated with an In Progress section and a Complete section. Checklists may live in In Progress but must be deleted when the plan moves to Complete.
    - **Completion:** Once a plan is completed, tested, and committed, rename the planning document to suffix it with `-complete.md` and delete the accompanying checklist file.

## Coding Standards

### Git Practices
- **Commit Style:** Use [Conventional Commits](https://www.conventionalcommits.org/) (e.g., `feat: ...`, `fix: ...`, `docs: ...`).
- **Frequency:** Commit regularly to ensure work is saved and history is granular.
- **Small Commits (Required):** Prefer very small, focused commits over large batches. Split work into logical, reviewable steps.

### Code Organization
- **Granularity:** Break functions down into very small units of functionality. Small functions are easier to test and reason about.
- **File Structure:**
    - **One Class Per File:** Adhere to a strict one-class-per-file rule.
    - **Exceptions:** Dataclasses (e.g., Pydantic models) and small Enum classes are permitted to coexist if strongly related.
- **Documentation:**
    - **Mandatory:** Document *every* function and class.
    - **Style:** Clear docstrings explaining purpose, parameters, and return values.

### Configuration Management
- **Storage:** JSON format.
- **Access Pattern:**
    - Never modify the JSON config file directly from the application code at runtime.
    - Always wrap configuration in a `Config` class.
    - The `Config` class must handle schema validation.
    - Access configuration values via accessor functions or properties on the `Config` class.
