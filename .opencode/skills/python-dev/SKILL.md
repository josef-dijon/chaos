# python-dev

## Purpose
Provide development guidelines for Python work in this repository.

## Core Rules
- Always use `uv` to run tests or scripts.
- Only run Python scripts or tests inside a virtual environment.
- Use `pytest` and `pytest-cov` for testing and coverage.
- Maintain test coverage greater than 95%.

## Design Principles
- Follow SOLID principles and DRY to reduce duplication.
- Keep functions small and focused; break up large functions.
- Favor clear, testable units over monoliths.
- Prefer explicit, readable code over cleverness.

## Python Practices
- Follow modern Python best practices.
- Use a canonical modern Python project layout.
- One class per file.
- Exceptions: small Enum classes and small data classes may coexist if strongly related.
- Write comprehensive module, class, and function docstrings.

## Configuration Rules
- Never modify JSON config files at runtime.
- Always wrap JSON configuration in a dedicated class.
- The wrapper class must validate schema and expose accessor methods.

## Process Discipline
- Always refer to architecture and specification documents before implementation.
- Always consult the current planning document for the work in progress.
