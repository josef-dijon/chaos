# **CHAOS: Cognitive Hierarchical Adaptive OS**

**Architecture Version:** 1.5.0 (Architecture Audit Pass)

## **1. Executive Summary**

CHAOS is a framework for building self-improving, persistent digital entities. It utilizes a dual-process theory of mind: every **Agent of CHAOS** consists of an **Actor** (the active, task-oriented consciousness) and a **Subconscious** (the background process responsible for reflection, maintenance, and growth). This structure ensures that agents do not just perform tasks, but adapt based on their experiences and direct "Architect" feedback.

## **2. Core Class Hierarchy**

### **2.1 The Agent (The Conscious Entity)**

The Agent is the primary container for a digital identity. It is the high-level interface through which the Architect (the user) interacts with the system. It orchestrates the relationship between the active self and the hidden self.

* **Philosophy:** Human intelligence is not a single loop; it is a hierarchy. The Agent class represents this totality, ensuring that execution and evolution are coupled but distinct.  
* **Attributes:**  
  * actor: An instance of BasicAgent dedicated to real-world task execution.  
  * subconscious: An instance of BasicAgent dedicated to analyzing the actor's logs and managing the Identity.  
* **Public API:**  
  * do(task: str): Hands a prompt to the actor. This triggers the production agentic loop to perform work in the physical or digital world.  
  * learn(feedback: str): Initiates a training session. The subconscious reviews the actor's recent failures/successes against the Architect's feedback and updates the Identity.  
  * dream(): A maintenance routine where the subconscious reviews the actor's derived memory (primarily LTM), grades interactions by importance, and optimizes the retrieval index.

### **2.2 The BasicAgent (The Processing Engine)**

A BasicAgent is the functional implementation of an LLM loop. It is a "blank slate" that only takes on a personality and capability set once it is assigned an Identity.

* **Philosophy:** Intelligence should be decoupled from identity. The BasicAgent provides the "raw processing power" and "tool access," while the Identity provides the "character" and "values."  
* **Attributes:**  
  * identity: The Identity instance defining the agent’s instructions and core values.  
  * memory: A memory subsystem managing idetic/LTM/STM per persona.  
  * skills_library: Access to the central repository of skills.
  * knowledge_library: Access to the central RAG knowledge base.
  * graph: A LangGraph instance defining the specific agentic logic (e.g., a "Reasoning" loop vs. an "Optimization" loop). LangGraph is explicitly chosen over higher-level frameworks (e.g., CrewAI) to ensure granular traceability and deterministic control over the agent's state transitions.
  * tools: A list of Tool instances available for the agent to call.  
* **Public API:**  
  * execute(input: str): Runs the LangGraph loop to process the input and return a response.  
  * refresh(): Reloads the Identity from disk to ensure any background "patches" are active.

### **2.3 The Identity (The Essence)**

The Identity is a persistent, schema-validated JSON file. It represents the immutable core and the mutable operational instructions of an agent.

* **Philosophy:** In a Single-Human Enterprise, agents must be digital assets. The Identity allows an agent to be serialized to disk, version-controlled via Git, and moved between environments without losing its "self."  
* **Attributes:**  
  * agent_id: The unique identity key for an agent. **Source of truth is the filesystem** (directory name / filename), not the JSON contents.
  * profile: A struct containing the role and "Core Values" (Immutable Root). (A human-friendly display name may exist, but must not be required for identity.)
  * instructions: The "Operational Notes" and system prompts (Mutable Shell).  
  * loop_definition: A reference to the specific logic flow the agent follows.  
  * tool_manifest: A list of permitted tools.  
  * skills_whitelist: (Optional) List of allowed skill names. If null, all skills are allowed.
  * skills_blacklist: (Optional) List of forbidden skill names. (Mutually exclusive with whitelist).
  * knowledge_whitelist: (Optional) List of allowed knowledge domains.
  * knowledge_blacklist: (Optional) List of forbidden knowledge domains. (Mutually exclusive with whitelist).
  * tool_whitelist: (Optional) List of allowed tool names (replaces tool_manifest in logic, though manifest is the legacy simplified version). 
  * memory: Configuration for the agent's memory model (paths, collection names, STM window size, STM heuristics). This is the primary control surface for tuning memory behavior.
* **Public API:**  
  * save(): Commits current state to the JSON file.  
  * patch_instructions(notes: str): Updates the mutable instructions (used by the subconscious after a learn or dream cycle).

#### **2.3.1 Identity Naming Contract (Source of Truth)**

* The agent id is derived from the identity filename.
* Identity files MUST be stored at:
  * `.chaos/identities/<agent_id>.identity.json`
* The filesystem path is the source of truth for `agent_id`. The JSON contents must not be treated as canonical for identity lookup.

#### **2.3.2 Identity Memory Configuration (Schema Contract)**

Identity MUST store memory behavior configuration (window sizes, heuristics, collection names). Connection details (DB URLs, credentials) are application configuration, not identity.

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
    "allow_subconscious_identity_updates": true,
    "allow_subconscious_memory_tuning": false
  }
}
```

### **2.4 The Memory System (The Temporal Link)**

This subsystem manages the memory layers required for persistent cognition.

* **Philosophy:** Real intelligence requires the ability to distinguish between "noise" (fetching a file) and "signal" (the realization that a specific coding pattern is flawed).  

#### **2.4.1 Memory Model (Idetic / Long-Term / Short-Term)**

CHAOS uses a 3-layer memory model **per agent** and **per persona**.

* **Personas:**
  * **Actor:** The interactive persona. Must never see or infer Subconscious memories.
  * **Subconscious:** The maintenance persona. Has access to all memory layers for both personas.

* **Layers (per persona):**
  * **Idetic Memory (Perfect Log):**
    * Append-only record of **all events**.
    * Retrieved literally by id or time range (no semantic search).
    * This is the **source of truth**; all other layers are derived from it.
  * **Long-Term Memory (LTM, Compacted Mirror):**
    * A 1:1 compacted representation of idetic events.
    * Searchable via RAG (vector search).
  * **Short-Term Memory (STM, Rolling Window):**
    * A rolling window of the last N **loop summaries**.
    * Each STM entry summarizes one user prompt loop and references multiple LTM ids.
    * Searchable as raw text via intelligent fuzzy search (with heuristics).

#### **2.4.2 Canonical Event Types & Loop Semantics**

All idetic events are tagged.

* **Required idetic fields (conceptual):**
  * `id`: unique id (uuid/ulid)
  * `ts`: timestamp (ISO-8601)
  * `agent_id`: owning agent
  * `persona`: `actor | subconscious`
  * `loop_id`: groups a single user prompt loop (used to build STM)
  * `kind`: one of:
    * `user_input`
    * `actor_output`
    * `tool_call`
    * `tool_result`
    * `subconscious_prompt`
    * `subconscious_output`
    * `system_event`
    * `error`
  * `visibility`: `external | internal`
  * `content`: the raw text payload (for now we log everything; redaction is a future feature)
  * `metadata`: optional structured data

* **STM loop summary rules:**
  * Exactly one STM entry is produced per `loop_id`.
  * The STM entry contains `ltm_ids[]` referencing all LTM entries created during that loop.

##### **2.4.2.1 Prompt Loop Boundaries (`loop_id`)**

* A `loop_id` is generated at the start of a single Architect invocation of `do(task)`.
* The loop includes, in order:
  * the `user_input` event
  * any number of `tool_call` / `tool_result` pairs
  * the final `actor_output`
* A loop ends when the Actor returns the final response for that `do(task)`.
* The Subconscious may read all Actor loops, but its own `learn()` / `dream()` operations MUST generate their own separate `loop_id` values under `persona=subconscious`.

#### **2.4.3 Search Interfaces (Conceptual)**

* **Idetic (literal):** `get_by_id(id)`, `get_range(start_ts, end_ts)`
* **LTM (RAG):** `rag_query(text, filters)`
* **STM (fuzzy):** `fuzzy_query(text, heuristics)` where heuristics (weights/thresholds) come from the agent's Identity.

##### **2.4.3.1 Derivation Pipelines (Consistency Rules)**

* **Idetic write is primary:** an idetic event is written first and is never mutated (append-only).
* **LTM derivation is 1:1:** for every idetic event, exactly one LTM entry is produced.
  * LTM entries store compacted text (summary) and metadata; embeddings live in the vector store.
* **STM derivation is per-loop:** at the end of a `loop_id`, one STM entry is produced summarizing the loop.
  * An STM entry references the list of LTM entry ids produced during that loop.

Failure handling:
* If LTM derivation or embedding fails, the raw DB must record a retryable status (e.g., `pending_embedding`).
* Idetic events must still be committed even when derived layers fail.
* Background reconciliation (dream cycle) is responsible for backfilling derived layers to match idetic coverage.

##### **2.4.3.2 STM Fuzzy Search (Algorithm + Scoring)**

STM is searched as raw text using fuzzy matching plus heuristic weighting.

* **Engine:** RapidFuzz (or equivalent) operating on normalized text.
* **Base similarity:** e.g. `token_set_ratio(query, stm_entry.summary)` in range 0-100.
* **Heuristic score:**
  * recency weight computed by exponential decay using `recency_half_life_seconds`
  * kind + visibility boosts come from Identity config

Conceptual scoring:

```text
similarity = token_set_ratio(query, summary) / 100.0
recency = exp(-ln(2) * age_seconds / half_life_seconds)
boost = kind_boosts[kind] * visibility_boosts[visibility]
score = (w_similarity * similarity + w_recency * recency) * boost
```

The heuristics object is stored in Identity and may be tuned (potentially by the Subconscious, depending on `tuning_policy`).

#### **2.4.4 Storage Layout (Global Raw DB + Separate Vector Store)**

CHAOS separates **raw text persistence** from **vector retrieval**.

**CHAOS_HOME (project-local):** All CHAOS artifacts live under `.chaos/` in the current project directory. No CHAOS-managed state may be created in the project root.

Canonical local-dev layout:
```text
.chaos/
  identities/
    <agent_id>.identity.json
  db/
    raw.sqlite
    chroma/
```

* **Identity (local dev):**
  * Filesystem is the current source of truth for identity.
  * Identity files are stored under `.chaos/identities/`.
  * Future: identity may be mirrored into the raw memory DB for fleet management, but is not required for the memory model.

* **Global Raw Memory DB (Idetic + LTM/STM raw text):**
  * Stores the canonical idetic event log plus the raw text payloads for derived layers.
  * Designed to run as a dedicated database service (Docker container) in production.
  * Local dev default: a file-based DB at `.chaos/db/raw.sqlite`.
  * Schema (SQLite/Postgres compatible, conceptual DDL):

```sql
-- Canonical schema version for migrations
CREATE TABLE IF NOT EXISTS schema_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- Idetic: append-only event log
CREATE TABLE IF NOT EXISTS idetic_events (
  id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  persona TEXT NOT NULL,
  loop_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  visibility TEXT NOT NULL,
  content TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_idetic_agent_persona_ts
  ON idetic_events(agent_id, persona, ts);
CREATE INDEX IF NOT EXISTS idx_idetic_agent_persona_loop
  ON idetic_events(agent_id, persona, loop_id);

-- LTM: 1:1 compacted mirror of idetic
CREATE TABLE IF NOT EXISTS ltm_entries (
  id TEXT PRIMARY KEY,
  idetic_id TEXT NOT NULL UNIQUE,
  ts TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  persona TEXT NOT NULL,
  loop_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  visibility TEXT NOT NULL,
  summary TEXT NOT NULL,
  importance REAL NOT NULL DEFAULT 0.0,
  embed_status TEXT NOT NULL DEFAULT 'pending',
  metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_ltm_agent_persona_ts
  ON ltm_entries(agent_id, persona, ts);
CREATE INDEX IF NOT EXISTS idx_ltm_agent_persona_loop
  ON ltm_entries(agent_id, persona, loop_id);

-- STM: per-loop summaries
CREATE TABLE IF NOT EXISTS stm_entries (
  id TEXT PRIMARY KEY,
  ts_start TEXT NOT NULL,
  ts_end TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  persona TEXT NOT NULL,
  loop_id TEXT NOT NULL,
  summary TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  UNIQUE(agent_id, persona, loop_id)
);
CREATE INDEX IF NOT EXISTS idx_stm_agent_persona_ts_end
  ON stm_entries(agent_id, persona, ts_end);

-- Map STM -> LTM (ordered)
CREATE TABLE IF NOT EXISTS stm_ltm_map (
  stm_id TEXT NOT NULL,
  ltm_id TEXT NOT NULL,
  seq INTEGER NOT NULL,
  PRIMARY KEY (stm_id, ltm_id)
);
CREATE INDEX IF NOT EXISTS idx_stm_ltm_stm_seq
  ON stm_ltm_map(stm_id, seq);
```

* **Vector Store (LTM embeddings only):**
  * Stores embeddings keyed by `ltm_entry_id` from the raw memory DB.
  * Runs as a separate service from the raw memory DB (Docker container) in production.
  * Local dev default: Chroma persistence under `.chaos/db/chroma/`.
  * Collections are partitioned by agent + persona:
    * `<agent_id>__actor__ltm`
    * `<agent_id>__subconscious__ltm`

Vector item contract:
* **Document id:** MUST equal `ltm_entries.id` (string).
* **Document text:** MUST be `ltm_entries.summary`.
* **Metadata:** MUST include at least:
  * `agent_id`, `persona`, `kind`, `visibility`, `ts`, `loop_id`, `importance`
* **Filters:** Actor retrieval MUST filter to `agent_id=<agent_id>` and `persona=actor`.
* **Deletions:** If an LTM entry is deleted (future), the corresponding vector item must be deleted by id.

#### **2.4.5 Access Rules (Non-Negotiable)**

* **Actor access:** may query only `actor` idetic/LTM/STM for its own `agent_id`.
* **Subconscious access:** may query all layers for both personas (actor + subconscious) for its `agent_id`.
* **Prompt hygiene:** Actor prompts must never include Subconscious events, summaries, or derived memories.

#### **2.4.6 Isolation Enforcement (Mechanism + Tests)**

The access rules above must be enforced in code by construction.

* Introduce a persona-scoped repository/wrapper (conceptual):
  * `ActorMemoryView(agent_id)`:
    * only ever queries `persona=actor`
    * only ever uses the `agent_id__actor__ltm` collection
  * `SubconsciousMemoryView(agent_id)`:
    * may query both personas and both collections
* Unit tests MUST assert:
  * Actor retrieval never returns `persona=subconscious` rows from the raw DB.
  * Actor vector queries never hit `<agent_id>__subconscious__ltm`.
  * Actor prompt construction contains no Subconscious-only events.

### **2.5 The Tool (The External Interface)**

An abstract class that unifies local CLI execution and remote Model Context Protocol (MCP) servers.

* **Attributes:**  
  * type: CLI or MCP.  
  * schema: The JSON description of the tool's arguments (for the LLM).  
* **Public API:**  
  * call(args: dict): Executes the tool and returns the text output.

### **2.6 The Tool Library**

A centralized registry of all available tools in the system.

* **Philosophy:** Tools should be modular and discoverable. The Library acts as the warehouse from which an Agent's Identity selects its capability set.
* **Attributes:**
  * registry: A dictionary mapping tool names to Tool instances.
* **Public API:**
  * get_tool(name): Retrieves a specific tool.
  * list_tools(whitelist, blacklist): Returns a list of tools available to a specific Identity.
  * *Future:* Librarian Agent - An intelligent sub-agent that finds the best tool for a complex request.

### **2.7 The Skills Library**

A centralized repository of reusable capabilities and prompt patterns (distinct from executable Tools).

* **Philosophy:** Instead of hardcoding prompts into the agent, they are stored as modular "skills" that can be dynamically loaded or restricted by the Identity.
* **Attributes:**
  * registry: A dictionary mapping skill names to their definitions (prompts/logic).
* **Public API:**
  * get_skill(name): Retrieves a specific skill.
  * list_skills(): Returns available skills.
  * *Future:* Librarian Agent - An intelligent sub-agent that finds the most relevant skills for a task.

### **2.8 The Knowledge Library**

A centralized RAG system for static or reference knowledge (distinct from the agent's autobiographical memory).

* **Philosophy:** Agents need access to documentation, best practices, and codebase knowledge that is curated and distinct from their personal experiences. The Subconscious has full access to this, while the Actor's access can be scoped by the Identity.
* **Attributes:**
  * store: A Vector Database containing indexed documents.

Relationship to Autobiographical LTM:
* The Knowledge Library is curated, mostly-static reference content (docs, codebase knowledge).
* Autobiographical LTM is personal experience derived from idetic events.
* They may run on the same underlying vector technology, but MUST be separated by collections and access rules.
  * Knowledge collections: organization/project scoped.
  * LTM collections: `<agent_id>__<persona>__ltm`.
* The Subconscious has full access to Knowledge.
* The Actor's access to Knowledge can be whitelisted/blacklisted by Identity (knowledge_whitelist/knowledge_blacklist).
* **Public API:**
  * search(query, limit): Semantic search for knowledge snippets.
  * *Future:* Librarian Agent - An intelligent sub-agent that performs multi-step research to answer a query.

## **3. Operations & Lifecycle**

### **3.1 The Learning Circuit**

When learn() is called, the Agent enters a restricted state. The Subconscious is given access to all memory (Actor + Subconscious; idetic + derived layers) and the Architect's feedback.

Learning steps (conceptual):

1. **Collect context:** Select the relevant recent Actor loops (by time range, loop ids, or explicit ids) plus the Architect feedback.
2. **Propose patch:** Generate a minimal patch to Identity (normally `instructions.operational_notes`).
3. **Shadow simulation:** Execute a test task using a "Shadow Actor" (same toolset, updated instructions).
4. **Score improvement:** Evaluate the Shadow result vs a rubric:
   * task completion correctness
   * instruction adherence
   * safety/tool constraints
   * latency/verbosity constraints (if applicable)
5. **Apply patch:** If the score improves, patch Identity on disk.

Tuning levers:
* The Subconscious may also propose memory heuristic tuning (STM search heuristics / window sizes).
* Whether those changes can be applied automatically is controlled by `tuning_policy.allow_subconscious_memory_tuning`.

### **3.2 The Dreaming Cycle**

dream() is an asynchronous or idle-time process. The Subconscious performs maintenance over the memory system and retrieval indices.

Dream tasks (conceptual):

* **Reconciliation:** Ensure derived layers mirror idetic coverage.
  * Create missing `ltm_entries` for any `idetic_events` without a 1:1 mirror.
  * Create missing `stm_entries` for any completed loops missing summaries.
* **Importance grading:** Assign/adjust `ltm_entries.importance` based on heuristics:
  * repetitive low-value events -> lower importance
  * pivotal decisions, user corrections -> higher importance
* **Embedding backfill:** For any `ltm_entries.embed_status='pending'`, generate embeddings and upsert into the vector store.
* **Re-indexing semantics:** "Re-index" means updating vector metadata (importance, tags) and ensuring the vector store contains the correct set of embedded LTM ids.

## **4. Roadmap: From CLI to Enterprise**

### **4.1 The MVP (CLI Prototype)**

The initial implementation will be a Python CLI for rapid iteration on the memory and learning logic.

* The Architect interacts with a single "Agent of CHAOS" (e.g., a "Coder").  
* The do command is standard input.  
* The learn and dream commands are manual triggers (e.g., /learn [feedback]).  
* Output is color-coded to simulate the "Mirror Persona" (Actor = Green, Subconscious = Blue).

### **4.2 Scaling to a Team**

In a team environment, multiple Agent instances will exist. They will communicate via the do() API. The subconscious of each agent will monitor inter-agent communications for "misunderstandings," triggering a learn cycle if the team dynamic breaks down.

### **4.3 The Mattermost View Layer**

The future "Digital Headquarters" will integrate CHAOS into Mattermost.

* **Actor:** Posts as a standard Bot user in public channels.  
* **Subconscious:** Only appears in "Training GDMs" or as a "Mirror" alias in private threads when the agent is in learn mode.  
* **Identity Management:** Mattermost Playbooks will provide a visual UI to view the "Health" and "Instructions" stored in each agent's Identity.

## **5. Operational Concerns (Local Dev -> Services)**

CHAOS uses two separate persistence services:

* **Raw Memory DB (authoritative, text + metadata):**
  * Local dev default: SQLite file `.chaos/db/raw.sqlite`.
  * Production target: a dedicated DB service (Docker container), suitable for concurrency (e.g., Postgres).
  * Transactions: idetic write + LTM row insert should be in a single transaction when possible.
  * Concurrency: prefer many readers + moderate writers; heavy concurrent writes should be handled with batching or a single-writer queue.

* **Vector Store (embeddings only):**
  * Local dev default: `.chaos/db/chroma/`.
  * Production target: a dedicated vector service (Docker container).
  * Upserts must be idempotent on `ltm_entries.id`.

Backup / restore:
* Backup `.chaos/identities/` + raw memory DB + vector store persistence.
* Restore must keep the raw DB ids stable to preserve the vector id mapping.

## **6. Security & Redaction Roadmap**

Current posture (explicitly temporary):
* All tool inputs/outputs and messages are logged to idetic memory.

Planned hardening:
* Redaction policy at ingestion (preferred) for known secret patterns and high-risk tool outputs.
* Optional encryption at rest for raw memory DB.
* Metadata tagging for sensitive events (`metadata.sensitivity`).
* Retrieval-time safety filters to prevent sensitive tool output from being surfaced in the Actor prompt.

## **7. Migration & Versioning Policy**

* Identity must include `schema_version`.
* Raw DB schema must include a `schema_meta` record for schema version.
* Migrations must be explicit, forward-only, and tested.
  * Identity migrations: transform JSON to the newest schema.
  * Raw DB migrations: apply SQL migrations.
  * Vector store migrations: rebuild from `ltm_entries` when necessary.
