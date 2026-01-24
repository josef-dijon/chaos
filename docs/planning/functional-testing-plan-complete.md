# Plan: Functional Testing Suite

## 1. Objective
Verify the end-to-end integration of the CHAOS framework (Actor, Subconscious, Memory, and Tools) using real OpenAI API calls and ChromaDB persistence.

## 2. Strategy
- **Framework:** `pytest`
- **Isolation:** Each test will run in a unique temporary directory using the `tmp_path` fixture to ensure `identity.json` and `chroma_db/` do not interfere with the development environment or other tests.
- **Execution:** Tests will be executed via `uv run pytest tests/functional`.

## 3. Test Scenarios
### 3.1 CLI Initialization
- Command: `chaos init`
- Verification: Assert `identity.json` exists and contains the default `Chaos` profile.

### 3.2 Actor & Tool Integration
- Command: `chaos do "Write 'Hello CHAOS' to a file named test_output.txt"`
- Verification: Assert `test_output.txt` exists and contains the correct string. This verifies the `FileWriteTool` and the LangGraph loop.

### 3.3 Memory Persistence (LTM/STM)
- Command 1: `chaos do "My secret code is 1234"`
- Command 2: `chaos do "What is my secret code?"`
- Verification: Assert the agent's response contains "1234". This verifies ChromaDB retrieval and context injection.

### 3.4 Learning Circuit (Subconscious)
- Command 1: `chaos learn "Always respond like a pirate"`
- Command 2: `chaos do "Say hello"`
- Verification: 
    1. Assert `identity.json` was patched with the new operational note.
    2. Assert the response to "Say hello" uses pirate dialect (e.g., "Ahoy!").

## 4. Dependencies
- Valid `OPENAI_API_KEY` in `.env`.
- `chromadb` and `langchain-openai` installed.
