# **LLM Primitive Architecture**

**Project:** The Maker's Warren AI Infrastructure

**Author:** Joe (Architect) & Gemini (Assistant)

**Version:** 1.8

**Status:** Design Baseline

## **1\. Executive Summary**

A high-reliability, vendor-agnostic, and cost-aware infrastructure for executing structured AI tasks. This architecture prioritizes **Precision** (correct Pydantic data), **Resilience** (surviving outages), and **Observability** (centralized cost/usage auditing).

## **2\. Technical Dependencies**

To implement this stack, the following Python packages are required:

* **instructor**: Handles the Pydantic-to-Schema mapping and response validation.  
* **litellm**: Provides the abstraction layer for multi-vendor support and the Proxy server functionality.  
* **tenacity**: Retrying library for handling transient API/Network errors with exponential backoff.  
* **pydantic**: The foundation for data modeling and logic-based validation.  
* **tiktoken**: OpenAI’s fast BPE tokenizer for local token counting and pre-flight cost estimation.

## **3\. The "Reliability Turducken" Stack**

The core execution pipeline consists of four distinct layers, organized in a strict ownership hierarchy to ensure separation of concerns.

### **Ownership Chain**

BaseManager (Strategy) ⮕ LLMService (Abstraction) ⮕ StableTransport (Shielding) ⮕ LiteLLM Proxy (Transport)

| Component | Ownership | Primary Responsibility |
| :---- | :---- | :---- |
| **Manager** | System Root | Orchestration, Multi-turn logic, "The Nudge" |
| **LLMService** | Manager | Exception concealment, Request/Response mapping |
| **StableTransport** | LLMService | Connection shielding, Exponential backoff |
| **LiteLLM Proxy** | Independent | Routing, Key management, Usage auditing |

## **4\. The Multi-Turn Logic Loop (Manager Layer)**

The Manager manages a stateful conversation to "nudge" models toward valid output. It treats the LLM as a functional unit: execute(Request) \-\> Response.

### **Error Scraping & Feedback**

When the Response indicates a SEMANTIC\_ERROR, the Manager extracts Pydantic error details and appends them to the conversation history as a correction prompt.

* **Logic Retry Policy:** High tolerance (e.g., 5 attempts).  
* **Structural Retry Policy:** Low tolerance. If the model cannot produce valid JSON within the nudge limit, the task is aborted.

## **5\. Data-Driven Model Selection**

The architecture uses historical performance data via a dedicated StatsService to select the optimal model for a given task.

### **Safety Ceiling (The 2nd Sigma)**

The ModelSelector uses a statistical buffer for budgeting:

## **![][image1]6\. Centralized Auditing & Metadata**

All usage data is offloaded to the **LiteLLM Proxy Server**. The LLMService ensures every request contains a metadata block identifying the manager\_id and attempt number for granular auditing.

## **7\. Global Configuration**

A singleton Config class serves as the source of truth for infrastructure secrets (Proxy URLs, Master Keys), preventing configuration leakage into the business logic layers.

## **8\. Container Orchestration & Data Flow**

1. **Write Flow:** Proxy calculates cost and performs a SQL INSERT into PostgreSQL.  
2. **Read Flow:** AI System (Manager) makes HTTP GET requests to Proxy endpoints for performance metrics.

## **9\. Database Administration & Monitoring**

* **Primary Monitoring (pgweb):** Lightweight browser for quick read-only peeks.  
* **Full Administration (pgAdmin 4):** Heavy-duty interface for schema mutations.  
* **Infrastructure Monitoring (LiteLLM UI):** High-level dashboard for spend/latency.

## **10\. Object-Oriented Design Model**

The implementation follows a functional response pattern to eliminate try/except bloat in the business logic.

### **Core Classes**

* **LLMRequest**: Encapsulates prompt, schema, budget, and history.  
* **LLMResponse**: A unified object containing status, data, and detailed error\_details.  
* **LLMService**: The "Black Box" that swallows mechanical exceptions and returns a Response.

## **11\. Error State Mapping (ResponseStatus)**

| Status | Architectural Trigger | Recovery Strategy |
| :---- | :---- | :---- |
| SUCCESS | Pydantic validation passed | Return data to caller |
| SEMANTIC\_ERROR | Schema mismatch or Type error | "The Nudge" (Logic Retry) |
| MECHANICAL\_ERROR | Transport retries exhausted (500/503/Timeout) | Escalate to higher-tier model or abort |
| CAPACITY\_ERROR | Context window overflow | Truncate history or scale model |
| CONFIG\_ERROR | Invalid Auth, Keys, or Metadata | Critical Alert / Halt System |
| BUDGET\_ERROR | No model matches requested constraints | Relax budget or task priority |

## **12\. Implementation Priorities**

1. **Phase 1:** Standardize the "Resilient Pipe" (StableTransport).  
2. **Phase 2:** Implement the LLMService functional wrapper.  
3. **Phase 3:** Build the BaseManager logic loop and "Nudge" scraper.  
4. **Phase 4:** Finalize ModelSelector using Proxy API stats.

## **13\. Class Hierarchy**

`import instructor`  
`import json`  
`import httpx`  
`import numpy as np`  
`from litellm import completion, exceptions as litellm_exceptions`  
`from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError`  
`from pydantic import BaseModel, Field, ValidationError`  
`from typing import Type, List, Dict, Any, Optional, Union`  
`from enum import Enum`

`# --- SECTION 0: GLOBAL CONFIGURATION ---`

`class Config:`  
    `"""`  
    `Global configuration singleton for the workshop.`  
    `In production, these pull from environment variables.`  
    `"""`  
    `_PROXY_URL = "http://localhost:4000"`  
    `_MASTER_KEY = "sk-placeholder-key"`

    `@classmethod`  
    `def get_litellm_proxy_url(cls) -> str:`  
        `return cls._PROXY_URL`

    `@classmethod`  
    `def get_litellm_proxy_master_api_key(cls) -> str:`  
        `return cls._MASTER_KEY`

`# --- SECTION 1: DOMAIN OBJECTS ---`

`class UsageStats(BaseModel):`  
    `"""Container for historical performance data fetched from LiteLLM Proxy."""`  
    `model_id: str`  
    `manager_id: str`  
    `avg_output_tokens: float = 0.0`  
    `std_dev_output_tokens: float = 0.0`  
    `avg_latency: float = 0.0`  
    `total_cost_usd: float = 0.0`

    `@property`  
    `def safety_ceiling(self) -> float:`  
        `"""The 95% confidence interval (Mean + 2 Sigma) for output tokens."""`  
        `return self.avg_output_tokens + (2 * self.std_dev_output_tokens)`

`class AIModel(BaseModel):`  
    `"""Definition of an LLM capability in the system."""`  
    `name: str`  
    `proxy_name: str`  
    `tags: List[str]`  
    `cost_per_1k_input: float`  
    `cost_per_1k_output: float`

`class LLMRequest(BaseModel):`  
    `"""Encapsulates everything needed for a single LLM execution."""`  
    `prompt: str`  
    `schema: Type[BaseModel]`  
    `model: AIModel`  
    `manager_id: str`  
    `budget: float`  
    `tag: str = "fast"`  
    `history: List[Dict] = []`  
    `attempt: int = 0`  
    `dry_run: bool = false`

`class ResponseStatus(Enum):`  
    `SUCCESS = "success"`  
    `SEMANTIC_ERROR = "semantic_error"   # Pydantic/Schema fail`  
    `MECHANICAL_ERROR = "mechanical_error" # Transport/Network fail`  
    `CAPACITY_ERROR = "capacity_error"     # Context window`  
    `CONFIG_ERROR = "config_error"         # Auth/Keys/Missing Config`  
    `BUDGET_ERROR = "budget_error"         # Cost/Selection`

`class LLMResponse(BaseModel):`  
    `"""The unified result of an LLM execution."""`  
    `status: ResponseStatus`  
    `data: Optional[Any] = None`  
    `error_message: Optional[str] = None`  
    `error_details: Optional[Dict] = None`   
    `raw_response: Optional[Any] = None`  
    `metadata: Dict = {}`  
    `actual_cost: float = 0.0`  
    `actual_time: float = 0.0`  
    `estimated_cost: float = 0.0`  
    `estimated_time: float = 0.0`  
    

`# --- SECTION 2: INFRASTRUCTURE ---`

`class StableTransport:`  
    `"""Layer 4: The Shielded Pipe. Handles retries for transient networking/provider issues."""`  
    `def __init__(self, proxy_url: str, master_key: str):`  
        `self.proxy_url = proxy_url`  
        `self.master_key = master_key`

    `@retry(`  
        `stop=stop_after_attempt(5),`  
        `wait=wait_exponential(multiplier=1, min=2, max=30),`  
        `retry=retry_if_exception_type((`  
            `litellm_exceptions.ServiceUnavailableError,`  
            `litellm_exceptions.InternalServerError,`  
            `litellm_exceptions.RateLimitError,`  
            `litellm_exceptions.Timeout,`  
            `httpx.ConnectError,`  
            `httpx.ReadTimeout`  
        `))`  
    `)`  
    `def call(self, model_name: str, messages: List[Dict], **kwargs) -> Any:`  
        `return completion(`  
            `model=model_name,`  
            `messages=messages,`  
            `api_base=self.proxy_url,`  
            `api_key=self.master_key,`  
            `**kwargs`  
        `)`

`class ModelStatsService:`  
    `"""Layer 3: The Auditor. Client for the LiteLLM Proxy REST API."""`  
    `def __init__(self):`  
        `self.url = Config.get_litellm_proxy_url()`  
        `self.key = Config.get_litellm_proxy_master_api_key()`

    `def get_model_stats(self, manager_id: str, model_name: str) -> UsageStats:`  
        `"""Queries LiteLLM Proxy for historical performance metrics."""`  
        `# TODO: Implement real REST call to /spend/logs`  
        `return UsageStats(`  
            `model_id=model_name,`  
            `manager_id=manager_id,`  
            `avg_output_tokens=250.0,`  
            `std_dev_output_tokens=45.0`  
        `)`

`class BlockStatsService:`  
    `def get_average_block_time() -> float:`  
        `pass`  
    `def get_average_block_cost() -> int:`  
        `pass`  
    `def get_reliability_rate() -> float:`  
        `pass`  
    `def get_number_llm_calls() -> int:`  
        `pass`  
    `def get_number_blocks_executed() -> int`  
        `pass`  
    `def add_block_stat(time: float, cost: int, success: bool):`  
        `pass`

`# --- SECTION 3: INTELLIGENCE ---`

`class ModelSelector:`  
    `"""Layer 3: The Financial Brain. Handles budgeting and model picking."""`  
    `def __init__(self, stats_service: StatsService, catalog: List[AIModel]):`  
        `self.stats_service = stats_service`  
        `self.catalog = catalog`

    `def select_best_model(self, manager_id: str, budget: float, required_tag: str) -> AIModel:`  
        `valid_models = [m for m in self.catalog if required_tag in m.tags]`  
        `candidates = []`  
        `for model in valid_models:`  
            `stats = self.stats_service.get_model_stats(manager_id, model.proxy_name)`  
            `est_cost = (model.cost_per_1k_output / 1000) * stats.safety_ceiling`  
            `if est_cost <= budget:`  
                `candidates.append((est_cost, model))`  
          
        `if not candidates:`  
            `raise ValueError(f"No models found matching tag '{required_tag}' within budget ${budget}")`  
              
        `return min(candidates, key=lambda x: x[0])[1]`

`class LLMService:`  
    `"""`  
    `Layer 2: The Abstraction Layer.`  
    `Owns the Transport and provides a clean execute(Request) -> Response interface.`  
    `"""`  
    `def __init__(self):`  
        `url = Config.get_litellm_proxy_url()`  
        `key = Config.get_litellm_proxy_master_api_key()`  
        `self.transport = StableTransport(url, key)`  
        `self.validator_client = instructor.from_litellm(self.transport.call)`

    `def execute(self, request: LLMRequest) -> LLMResponse:`  
        `messages = request.history + [{"role": "user", "content": request.prompt}]`  
        `metadata = {"manager_id": request.manager_id, "attempt": request.attempt}`  
          
        `try:`  
            `res = self.validator_client.chat.completions.create(`  
                `model=request.model.proxy_name,`  
                `response_model=request.schema,`  
                `messages=messages,`  
                `extra_body={"metadata": metadata}`  
            `)`  
            `return LLMResponse(status=ResponseStatus.SUCCESS, data=res)`

        `except ValidationError as e:`  
            `return LLMResponse(`  
                `status=ResponseStatus.SEMANTIC_ERROR,`  
                `error_message="Schema validation failed.",`  
                `error_details={"errors": e.errors()}`  
            `)`  
        `except RetryError as e:`  
            `return LLMResponse(`  
                `status=ResponseStatus.MECHANICAL_ERROR,`  
                `error_message=f"Transport retries exhausted: {str(e)}"`  
            `)`  
        `except litellm_exceptions.ContextWindowExceededError:`  
            `return LLMResponse(status=ResponseStatus.CAPACITY_ERROR, error_message="Context window exceeded.")`  
        `except (litellm_exceptions.AuthenticationError, litellm_exceptions.PermissionDeniedError):`  
            `return LLMResponse(status=ResponseStatus.CONFIG_ERROR, error_message="Auth failure.")`  
        `except Exception as e:`  
            `return LLMResponse(`  
                `status=ResponseStatus.MECHANICAL_ERROR,`  
                `error_message=f"Unexpected error: {type(e).__name__} - {str(e)}"`  
            `)`

`# --- SECTION 4: THE MANAGER ---`

`class BaseManager:`  
    `"""Layer 1: The Strategic Architect. Owns the state and logic loop."""`  
    `def __init__(self, manager_id: str, selector: ModelSelector):`  
        `self.manager_id = manager_id`  
        `self.selector = selector`  
        `self.llm = LLMService()`

    `def dry_run_task(self, prompt: str, schema: Type[BaseModel], budget: float, tag: str = "fast") -> LLMResponse:`  
        `pass`

    `def run_task(self, prompt: str, schema: Type[BaseModel], budget: float, tag: str = "fast") -> LLMResponse:`  
        `try:`  
            `model = self.selector.select_best_model(self.manager_id, budget, tag)`  
        `except ValueError as e:`  
            `return LLMResponse(status=ResponseStatus.BUDGET_ERROR, error_message=str(e))`

        `history = []`  
        `current_prompt = prompt`

        `for attempt in range(5):`  
            `request = LLMRequest(`  
                `prompt=current_prompt,`  
                `schema=schema,`  
                `model=model,`  
                `manager_id=self.manager_id,`  
                `budget=budget,`  
                `history=history,`  
                `attempt=attempt`  
            `)`  
              
            `response = self.llm.execute(request)`

            `if response.status == ResponseStatus.SUCCESS:`  
                `return response`

            `if response.status == ResponseStatus.SEMANTIC_ERROR:`  
                `history.append({"role": "user", "content": current_prompt})`  
                `# Scrape error for the Nudge`  
                `current_prompt = f"Previous output failed validation: {json.dumps(response.error_details)}. Please correct and try again."`  
                `continue`  
              
            `return response`

        `return LLMResponse(status=ResponseStatus.SEMANTIC_ERROR, error_message="Max retries reached.")`

`# --- EXAMPLE USAGE ---`

`if __name__ == "__main__":`  
    `# 1. Configuration of the Catalog`  
    `catalog = [`  
        `AIModel(name="Mini", proxy_name="gpt-4o-mini", tags=["fast", "cheap"], cost_per_1k_input=0.0001, cost_per_1k_output=0.0006)`  
    `]`

    `# 2. Wire up the stack`  
    `stats_svc = StatsService()`  
    `selector = ModelSelector(stats_svc, catalog)`  
    `manager = BaseManager("cnc_boss_01", selector)`

    `# 3. Define a simple schema`  
    `class Part(BaseModel):`  
        `name: str`  
        `dimensions: List[float]`

    `# 4. Run`  
    `# result = manager.run_task("Design a 10x10 cube.", Part, budget=0.01)`  
    `# print(result)`

[image1]: <data:image/png;base64,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>