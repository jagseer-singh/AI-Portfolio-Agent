# Week 1 Study Notes & Key Concepts

## 1. The Core Problem We Are Solving
LLMs are probabilistic text predictors. If asked *"What is Apple's current stock price?"*, an LLM without tools will hallucinate a believable-sounding number.
To get deterministic, real data, we use **tool calling** (function calling).

---

## 2. The Three Pieces of Tool Calling
When interfacing an LLM with external tools, three elements are needed:

1. **Request Schema (`GetAssetPriceRequest`)**:
   - Defines the exact shape of data the LLM must generate.
   - Example: `symbol: str`, `asset_class: AssetClass`, `currency: str = "USD"`.
   - Validated via Pydantic so bad/malformed parameters are rejected upfront.

2. **Response Schema (`AssetPriceResponse`)**:
   - Defines the exact shape returned by our Python code back to the LLM.
   - Example: `price: float`, `timestamp: str`, `source: str`.
   - Keeps tool outputs structured and predictable.

3. **Tool Definition / The "Menu" (`get_tool_definitions`)**:
   - Wraps the Request Schema inside the format required by the provider's API (e.g., OpenAI).
   - Contains:
     - `name`: Identifier the LLM outputs to invoke the tool.
     - `description`: Plain-English explanation. The LLM reads this to know *when* and *why* to use this tool.
     - `parameters`: JSON Schema auto-generated from Pydantic via `.model_json_schema()`.
     - `strict: True`: Guarantees the LLM's output conforms strictly to the schema.

> **Takeaway on vendor schemas:** You do not need to memorize OpenAI, Anthropic, or Gemini's exact JSON parameters format. Vendors change syntax over time. Focus on the core concept: **Menu (description + schema) -> LLM generates args -> You validate and run -> Return output.**

---

## 3. Tool Execution & The Dispatcher Pattern (`mock_data.py`)
- **Mock Price Book**: In early testing/evals, we use deterministic static dictionaries (`MOCK_PRICES`) so eval scores are reproducible across test runs.
- **The Dispatcher (`dispatch_tool_call`)**:
  1. Receives raw tool name and arguments dictionary from the LLM.
  2. Looks up the tool name in `TOOL_REGISTRY`.
  3. Uses Pydantic (`schema_cls.model_validate(arguments)`) to validate the input arguments.
  4. Calls the actual Python function (`execute_get_asset_price`).
  5. Serializes the response back to JSON via `.model_dump_json()`.

---

## 4. Why We Call the LLM Twice: The 2-Pass Industry Standard
Is the 2-pass approach standard in software engineering? **Yes, it is the universal pattern.**

```
User Prompt
     │
     ▼
[ PASS 1: The Decision Pass ] ──> LLM identifies tool & extracts arguments (JSON)
     │
     ▼
[ Intermission: Execution ]   ──> Your Python code validates (Pydantic) & runs locally
     │
     ▼
[ PASS 2: The Synthesis Pass ] ──> LLM receives tool output & composes human answer
```

- **Separation of Concerns**: The LLM is the *Brain* (decision maker); your server is the *Body* (sandbox & executor). For security and reliability, LLMs are never given raw access to external systems without local validation.
- **ReAct (N-Pass Loops)**: When queries require chained reasoning (e.g. fetch portfolio holdings $\rightarrow$ fetch live prices $\rightarrow$ calculate profit), this 2-pass flow loops $N$ times until no more tools are requested.

---

## 5. Building an LLM vs. Calling an LLM API
- **Building an LLM**: Pre-training massive neural networks on supercomputer clusters (OpenAI, Google, Anthropic).
- **Building an Agent**: Calling existing LLM APIs via HTTP and building the orchestration, tool registry, memory, RAG, and validation systems around it. We are building the agent body around the rented model brain.

---

## 6. Stateless History & Parallel Tool Calling (`llm_client.py`)
- **Why record `assistant_msg` before returning tool outputs?**
  OpenAI's Chat API is stateless. To return a message with `role: "tool"`, it must be immediately preceded by an `assistant` message containing the matching `tool_calls` and `id`. Otherwise, the API throws a 400 error.
- **Vendor Metadata & Thought Signatures**:
  Some providers (such as Google Gemini) attach metadata (`thought_signature`) inside tool calls. Using `msg.model_dump(exclude_unset=True)` preserves these fields so the tool loop never drops necessary cryptographic signatures.
- **Why loop over `tool_calls`?**
  Modern LLMs perform **Parallel Tool Calling**. If a prompt asks for both "Apple and Microsoft prices", the model can output multiple tool requests in a single turn (`AAPL` and `MSFT`). We iterate over all requested calls, run each locally, and send back all results together.

---

## 7. Trustworthy Evaluations ("Evals") (`run_eval.py` & `eval_cases.py`)
- **Why unit tests are not enough for LLMs**:
  LLMs return varied phrasing. We evaluate agent behavior along three deterministic checkpoints:
  1. **Tool selection**: Did it invoke the expected tool (or avoid tools for general questions)?
  2. **Parameter accuracy**: Did tool arguments contain the right symbols/tickers?
  3. **Content verification**: Does the generated text contain the ground-truth figures?
- **Handling Rate Limits (HTTP 429)**:
  Free-tier endpoints enforce strict Requests-Per-Minute (RPM). Since each agent turn makes 2 requests, rapid evals can trigger `429 Too Many Requests`. Production solutions:
  - **Eval Pacing**: Adding an inter-test delay (`--delay 4`) to stay below the RPM ceiling.
  - **Exponential Backoff**: Catching `429` inside the client and waiting 12s, 24s, etc., before retrying.
- **Traceability (The CSV Log)**:
  Every eval run logs to `evals/results/eval_log.csv` with the current **Git commit hash**, **model name**, **temperature**, and timestamp. This lets us immediately identify regressions whenever code or prompts change.
