# Agentic Tools and Skills

## Status
Draft

## Purpose
Define the tool abstraction and the registries for tools, skills, and knowledge.

## Scope
Tool interface, tool library, skills library, and knowledge library boundaries.

## Contents

### The Tool (External Interface)
An abstract class that unifies local CLI execution and remote Model Context Protocol (MCP) servers.

- Attributes:
  - `type`: CLI or MCP.
  - `schema`: JSON description of tool arguments for the LLM.
- Public API:
  - `call(args: dict)`: Execute the tool and return text output.

### The Tool Library
Central registry of all available tools in the system.

- Philosophy: Tools are modular and discoverable; the Library is the warehouse from which an Identity selects capabilities.
- Attributes:
  - `registry`: dictionary mapping tool names to Tool instances.
- Public API:
  - `get_tool(name)`
  - `list_tools(whitelist, blacklist)`
- Future: librarian agent to select tools for complex requests.

### The Skills Library
Central repository of reusable capabilities and prompt patterns, distinct from executable tools.

- Philosophy: Prompt patterns are modular skills loaded or restricted by Identity.
- Attributes:
  - `registry`: dictionary mapping skill names to skill definitions.
- Public API:
  - `get_skill(name)`
  - `list_skills()`
- Future: librarian agent to select skills for tasks.

### The Knowledge Library
Central RAG system for static or reference knowledge, distinct from autobiographical memory.

- Philosophy: Knowledge is curated and separate from personal experiences. Subconscious has full access; Actor access is scoped by Identity.
- Attributes:
  - `store`: vector database containing indexed documents.

Relationship to autobiographical LTM:
- Knowledge is curated, mostly-static reference content.
- Autobiographical LTM is personal experience derived from idetic events.
- Collections must be separated:
  - Knowledge collections: organization or project scoped.
  - LTM collections: `<agent_id>__<persona>__ltm`.
- Actor access is gated by `knowledge_whitelist` / `knowledge_blacklist`.

Public API:
- `search(query, limit)`
- Future: librarian agent for multi-step research.

## References
- [Agentic Architecture Index](index.md)
- [Architecture Index](../index.md)
