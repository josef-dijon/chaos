# Agentic Core Classes

## Status
Draft

## Purpose
Define the primary agentic classes and their responsibilities in the CHAOS agent model.

## Scope
Agent, BasicAgent, and Identity roles and public APIs. Detailed identity schema lives in the identity contract.

## Contents

### The Agent (The Conscious Entity)
The Agent is the primary container for a digital identity. It is the high-level interface through which the Architect (the user) interacts with the system. It orchestrates the relationship between the active self and the hidden self.

- Philosophy: Human intelligence is not a single loop; it is a hierarchy. The Agent class represents this totality, ensuring that execution and evolution are coupled but distinct.
- Attributes:
  - actor: BasicAgent dedicated to real-world task execution.
  - subconscious: BasicAgent dedicated to analyzing the actor's logs and managing Identity.
- Public API:
  - `do(task: str)`: Hands a prompt to the actor, triggering the production loop.
  - `learn(feedback: str)`: Subconscious reviews recent outcomes against Architect feedback and updates Identity.
  - `dream()`: Maintenance routine for memory grading and index optimization.

### The BasicAgent (The Processing Engine)
A BasicAgent is the functional implementation of an LLM loop. It is a blank slate that takes on personality and capability once it is assigned an Identity.

- Philosophy: Intelligence is decoupled from identity. BasicAgent provides raw processing and tool access; Identity provides character and values.
- Attributes:
  - identity: Identity instance defining instructions and core values.
  - memory: Memory subsystem managing idetic/LTM/STM per persona.
  - skills_library: Central repository of skills.
  - knowledge_library: Central RAG knowledge base.
  - graph: LangGraph instance defining the agentic logic (reasoning vs. optimization loops).
  - tools: Tool instances the agent may call.
- Public API:
  - `execute(input: str)`: Runs the LangGraph loop and returns a response.
  - `refresh()`: Reloads Identity from disk to apply patches.

### The Identity (The Essence)
Identity is a persistent, schema-validated JSON file representing immutable core values and mutable operational instructions of an agent.

- Philosophy: Agents are digital assets. Identity allows serialization to disk, version control, and transfer without losing the self.
- Attributes:
  - agent_id: Unique identity key; source of truth is the filesystem path.
  - profile: Role and core values (immutable root).
  - instructions: System prompts and operational notes (mutable shell).
  - loop_definition: Reference to the agent's logic flow.
  - tool_manifest: Permitted tools list (legacy simplified version).
  - skills whitelist/blacklist and knowledge whitelist/blacklist.
  - tool_whitelist (optional), replacing tool_manifest in logic.
  - memory: Configuration for memory behavior (collections, STM heuristics).
- Public API:
  - `save()`: Commit state to the JSON file.
  - `patch_instructions(notes: str)`: Update mutable instructions.

## References
- [Agentic Architecture Index](index.md)
- [Identity Contract](agentic-identity-contract.md)
- [Architecture Index](../index.md)
