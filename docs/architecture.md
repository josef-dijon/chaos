# **CHAOS: Cognitive Hierarchical Adaptive OS**

**Architecture Version:** 1.2.0 (Identity Refactor)

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
  * dream(): A maintenance routine where the subconscious reviews the actor's Long-Term Memory (LTM), grades interactions by importance, and optimizes the RAG index.

### **2.2 The BasicAgent (The Processing Engine)**

A BasicAgent is the functional implementation of an LLM loop. It is a "blank slate" that only takes on a personality and capability set once it is assigned an Identity.

* **Philosophy:** Intelligence should be decoupled from identity. The BasicAgent provides the "raw processing power" and "tool access," while the Identity provides the "character" and "values."  
* **Attributes:**  
  * identity: The Identity instance defining the agent’s instructions and core values.  
  * memory: A MemoryContainer managing short-term and long-term data.  
  * skills_library: Access to the central repository of skills.
  * knowledge_library: Access to the central RAG knowledge base.
  * graph: A LangGraph instance defining the specific agentic logic (e.g., a "Reasoning" loop vs. an "Optimization" loop).  
  * tools: A list of Tool instances available for the agent to call.  
* **Public API:**  
  * execute(input: str): Runs the LangGraph loop to process the input and return a response.  
  * refresh(): Reloads the Identity from disk to ensure any background "patches" are active.

### **2.3 The Identity (The Essence)**

The Identity is a persistent, schema-validated JSON file. It represents the immutable core and the mutable operational instructions of an agent.

* **Philosophy:** In a Single-Human Enterprise, agents must be digital assets. The Identity allows an agent to be serialized to disk, version-controlled via Git, and moved between environments without losing its "self."  
* **Attributes:**  
  * profile: A struct containing the name, role, and "Core Values" (Immutable Root).  
  * instructions: The "Operational Notes" and system prompts (Mutable Shell).  
  * loop_definition: A reference to the specific logic flow the agent follows.  
  * tool_manifest: A list of permitted tools.  
  * skills_whitelist: (Optional) List of allowed skill names. If null, all skills are allowed.
  * skills_blacklist: (Optional) List of forbidden skill names. (Mutually exclusive with whitelist).
  * knowledge_whitelist: (Optional) List of allowed knowledge domains.
  * knowledge_blacklist: (Optional) List of forbidden knowledge domains. (Mutually exclusive with whitelist).
  * tool_whitelist: (Optional) List of allowed tool names (replaces tool_manifest in logic, though manifest is the legacy simplified version). 
* **Public API:**  
  * save(): Commits current state to the JSON file.  
  * patch_instructions(notes: str): Updates the mutable instructions (used by the subconscious after a learn or dream cycle).

### **2.4 The MemoryContainer (The Temporal Link)**

This class manages the two types of memory required for persistent cognition.

* **Philosophy:** Real intelligence requires the ability to distinguish between "noise" (fetching a file) and "signal" (the realization that a specific coding pattern is flawed).  
* **Attributes:**  
  * ltm: A Long-Term Memory (Vector Database) storing every interaction and internal monologue token.  
  * stm: A Short-Term Memory (Rolling Buffer) providing the immediate context for the current task.  
* **Public API:**  
  * record(role, content, thinking_tokens, importance): Saves a new interaction.  
  * retrieve(query, importance_filter): Fetches relevant memories via semantic search.  
  * reweight(interaction_id, new_importance): Updates the priority of a specific memory (critical for the dream cycle).

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

A centralized RAG system for static or reference knowledge (distinct from the agent's autobiographical MemoryContainer).

* **Philosophy:** Agents need access to documentation, best practices, and codebase knowledge that is curated and distinct from their personal experiences. The Subconscious has full access to this, while the Actor's access can be scoped by the Identity.
* **Attributes:**
  * store: A Vector Database containing indexed documents.
* **Public API:**
  * search(query, limit): Semantic search for knowledge snippets.
  * *Future:* Librarian Agent - An intelligent sub-agent that performs multi-step research to answer a query.

## **3. Operations & Lifecycle**

### **3.1 The Learning Circuit**

When learn() is called, the Agent enters a restricted state. The subconscious is given access to the actor's recent logs and the Architect's feedback. It performs a "Shadow Simulation":

1. It proposes a change to the actor's operational instructions.  
2. It runs a test task against the "Shadow Actor" (the actor with the new instructions).  
3. If the result improves, it "patches" the Identity on disk.

### **3.2 The Dreaming Cycle**

dream() is an asynchronous or idle-time process. The subconscious iterates through the actor's LTM:

* It identifies repetitive or low-value data (e.g., successful tool pings) and marks them with low importance.  
* It identifies pivotal decisions or user corrections and marks them with high importance.  
* It re-indexes the Vector DB, ensuring that high-importance "lessons" have higher weight in future RAG retrievals.

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
