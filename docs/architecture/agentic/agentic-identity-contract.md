# Agentic Identity Contract

## Status
Draft

## Purpose
Specify the identity schema contract, naming rules, and memory configuration requirements.

## Scope
Identity attributes, naming source of truth, memory configuration, and tuning policy constraints.

## Contents

### Identity Definition
The Identity is a persistent, schema-validated JSON file representing the immutable core and mutable operational instructions of an agent.

#### Attributes
- `agent_id`: Unique identity key; source of truth is the filesystem path.
- `profile`: Role and core values (immutable root).
- `instructions`: System prompts and operational notes (mutable shell).
- `loop_definition`: Reference to the agent's logic flow.
- `tool_manifest`: Permitted tools list (legacy simplified version).
- `skills_whitelist` / `skills_blacklist`: Optional lists of allowed/forbidden skills (mutually exclusive).
- `knowledge_whitelist` / `knowledge_blacklist`: Optional lists of allowed/forbidden knowledge domains (mutually exclusive).
- `tool_whitelist`: Optional list of allowed tool names.
- `memory`: Memory configuration for collections, STM windows, and heuristics.

#### Public API
- `save()`: Commit state to the JSON file.
- `patch_instructions(notes: str)`: Update mutable instructions after learn/dream cycles.

### Identity Naming Contract (Source of Truth)
- Agent id is derived from the identity filename.
- Identity files must be stored at:
  - `.chaos/identities/<agent_id>.identity.json`
- Filesystem path is canonical for `agent_id`.

### Identity Memory Configuration (Schema Contract)
Identity must store memory behavior configuration (window sizes, heuristics, collection names). Connection details (DB URLs, credentials) are application configuration, not identity.

Minimal identity example (conceptual):

```json
{
  "schema_version": "1.0",
  "profile": {
    "role": "Assistant",
    "core_values": ["Helpful", "Harmless", "Honest"]
  },
  "instructions": {
    "system_prompts": ["You are a helpful assistant."],
    "operational_notes": []
  },
  "memory": {
    "actor": {
      "ltm_collection": "default__actor__ltm",
      "stm_window_size": 20,
      "stm_search": {
        "engine": "rapidfuzz",
        "algorithm": "token_set_ratio",
        "threshold": 60,
        "top_k": 8,
        "recency_half_life_seconds": 86400,
        "weights": {
          "similarity": 1.0,
          "recency": 1.0,
          "kind_boosts": {
            "user_input": 1.0,
            "actor_output": 0.9,
            "tool_call": 0.6,
            "tool_result": 0.7,
            "system_event": 0.3,
            "error": 1.2
          },
          "visibility_boosts": {
            "external": 1.0,
            "internal": 0.4
          }
        }
      }
    },
    "subconscious": {
      "ltm_collection": "default__subconscious__ltm",
      "stm_window_size": 50,
      "stm_search": {
        "engine": "rapidfuzz",
        "algorithm": "token_set_ratio",
        "threshold": 55,
        "top_k": 12,
        "recency_half_life_seconds": 604800,
        "weights": {
          "similarity": 1.0,
          "recency": 1.0,
          "kind_boosts": {
            "subconscious_prompt": 0.8,
            "subconscious_output": 1.0,
            "user_input": 1.0,
            "actor_output": 1.0
          },
          "visibility_boosts": {
            "external": 1.0,
            "internal": 1.0
          }
        }
      }
    }
  },
  "tuning_policy": {
    "whitelist": ["instructions.operational_notes"],
    "blacklist": [
      "schema_version",
      "tuning_policy",
      "memory.subconscious",
      "memory.actor",
      "loop_definition"
    ]
  }
}
```

## References
- [Agentic Architecture Index](index.md)
- [Agentic Core Classes](agentic-core-classes.md)
- [Architecture Index](../index.md)
