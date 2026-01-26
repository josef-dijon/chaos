# Core Architecture Overview

## Status
Draft

## Purpose
Summarize the legacy core architecture overview that informed the current CHAOS baseline.

## Scope
High-level principles, state model, modules, data flow, and testing expectations.

## Contents

### Principles
- Human-as-LLM: The human provides completions and tool calls based on full conversation context.
- Automated state management: The system manages message history and executes tool calls autonomously.
- Stateless execution: No persistence or checkpointing in the legacy baseline.
- Small, testable functions with explicit state transitions.
- One class per file; docstrings on all functions and classes.

### System Overview
The system is a Python package that builds a LangGraph state machine that:
1) Initializes with a System Prompt and User Message.
2) LLM Node: Displays full context and prompts the human for an LLM completion.
3) Router: Determines if the human provided a text response or a tool call.
4) Action Node: (Future) Executes tools and appends results to history.
5) Loops back to LLM Node until a final response is reached.

### State Model
The state uses LangGraph's message-based history:
- `messages`: A list of BaseMessage objects (System, Human, AI, Tool).

### Modules
- `src/chaos/state.py`: State structure and initialization using TypedDict and `add_messages`.
- `src/chaos/cli_io.py`: CLI input/output handling for displaying context and collecting human completions.
- `src/chaos/graph.py`: Graph construction, LLM node, and routing logic.
- `src/chaos/app.py`: CLI entrypoint wiring graph and CLI I/O.

### Data Flow
- CLI initializes state.
- Graph nodes update state sequentially and append to history.
- **Capability Gaps:** If a required tool is missing during execution, the system must return a structured error response rather than failing silently or hallucinating.
- End state contains both human responses and full history.

### Known Gaps
- No persistence of state beyond a session.
- No formal recovery policy or checkpointing.
- No block-level contract; relies on LangGraph nodes directly.

### Testing
- Unit tests mock CLI input to validate transitions and state updates.
- Tests run with `uv run pytest` and maintain >=95% coverage.

## References
- [Core Architecture Index](index.md)
- [Architecture Index](../index.md)
