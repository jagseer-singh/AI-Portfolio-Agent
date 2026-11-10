# Portfolio Management Agent — Architecture Document

> **Status**: Living document — updated incrementally each week.
> **Started**: Week 1 (2026-11-10)
> **Last updated**: Week 1

---

## 1. Project Vision

Build an AI-powered Portfolio Management Agent that can:
- Fetch and analyze prices across equities, bonds, gold, and crypto
- Access portfolio ledger data securely via MCP (Model Context Protocol)
- Retrieve unstructured market intelligence using hybrid search (vector + BM25)
- Provide grounded, citation-backed investment insights
- Execute deterministic math and validated trades via a controlled write path

The agent is designed for **interview demonstration** — every component is built to
illustrate production-grade patterns in AI engineering.

---

## 2. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Frontend (SSE)                        │
│                  [Week 11: streaming tokens]                 │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│                     Agent Framework                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  ReAct Loop  │  │  LLM Client  │  │  Memory / State   │  │
│  │  [Week 3]    │  │  [Week 1] ✓  │  │  [Week 3]         │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────────────┘  │
│         │                 │                                  │
│  ┌──────▼─────────────────▼──────────────────────────────┐  │
│  │              Tool Registry & Dispatcher               │  │
│  │              [Week 1] ✓                               │  │
│  └──┬────────┬────────┬────────┬────────┬────────────────┘  │
│     │        │        │        │        │                    │
│  ┌──▼──┐ ┌──▼──┐ ┌──▼───┐ ┌──▼──┐ ┌──▼────────────────┐  │
│  │Price│ │Hold-│ │Write │ │RAG  │ │MCP Client          │  │
│  │Tool │ │ings │ │Tool  │ │Tool │ │[Week 5]            │  │
│  │[W1]✓│ │[W2] │ │[W10] │ │[W6] │ └──────┬─────────────┘  │
│  └──┬──┘ └──┬──┘ └──┬───┘ └──┬──┘        │                 │
└─────┼───────┼───────┼────────┼────────────┼─────────────────┘
      │       │       │        │            │
┌─────▼───────▼───────▼──┐ ┌──▼────────────▼──────────────────┐
│   External APIs        │ │   PostgreSQL                      │
│   [Week 2: live data]  │ │   ┌────────────────────────────┐  │
│   • Equities           │ │   │ Portfolio Ledger (MCP)     │  │
│   • Bonds              │ │   │ [Week 4]                   │  │
│   • Gold               │ │   ├────────────────────────────┤  │
│   • Crypto             │ │   │ pgvector embeddings        │  │
│                        │ │   │ [Week 6]                   │  │
│                        │ │   ├────────────────────────────┤  │
│                        │ │   │ Suggestions table (write)  │  │
│                        │ │   │ [Week 10]                  │  │
│                        │ │   └────────────────────────────┘  │
└────────────────────────┘ └───────────────────────────────────┘
```

---

## 3. Week-by-Week Component Details

### Week 1 — Pydantic Schemas, Tool Calling & Eval Harness ✓

**Goal**: Establish deterministic tool calling and trustworthy evaluation.

#### 3.1.1 Pydantic Schema Design

Tool calls are forced into strict JSON using Pydantic v2 models:

| Schema | Purpose |
|--------|---------|
| `GetAssetPriceRequest` | Single asset lookup (symbol, asset_class, currency) |
| `GetMultipleAssetPricesRequest` | Batch lookup (list of single requests) |
| `AssetPriceResponse` | Single price result with source and timestamp |
| `MultipleAssetPricesResponse` | Batch result with error list for failed symbols |

**Key decisions**:
- `strict: True` in OpenAI tool definitions forces the model to comply with the JSON schema
- `AssetClass` is an enum to constrain the taxonomy
- Currency is ISO 4217 (3 chars) — Pydantic validates length

#### 3.1.2 Mock Data Layer

Static `MOCK_PRICES` dictionary with 16 assets across all classes:
- 8 equities (AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, JPM)
- 3 bonds (TLT, BND, AGG)
- 2 gold (GLD, XAUUSD)
- 3 crypto (BTC-USD, ETH-USD, SOL-USD)

A `dispatch_tool_call(name, args)` function validates args through Pydantic
before execution — the LLM cannot bypass schema validation.

#### 3.1.3 Eval Harness

The `make eval` command runs 25 test cases at temperature 0 and logs:

| Field | Source |
|-------|--------|
| `timestamp` | UTC ISO-8601 |
| `git_commit` | `git rev-parse --short HEAD` |
| `model_name` | From config / env |
| `temperature` | From config / env |
| `tool_called_correctly` | Did the agent call the expected tool? |
| `symbols_correct` | Were all expected symbols in tool args? |
| `answer_contains_expected` | Does the final answer contain expected substrings? |
| `overall_pass` | All three checks AND'd |

Results append to `evals/results/eval_log.csv` for historical tracking.

**Noise elimination**: Temperature 0 by default. If temperature > 0 is used,
the harness automatically runs each case 3 times and keeps the best result.

#### 3.1.4 Test Coverage

18 unit tests covering:
- Schema validation (valid/invalid inputs, edge cases)
- Mock data execution (single, batch, unknown symbols)
- Dispatch routing (tool routing, error handling)
- Tool definition structure (OpenAI format compliance)

---

### Week 2 — Capstone Setup & Multi-Asset APIs
*[Planned]*

### Week 3 — Manual ReAct Loop
*[Planned]*

### Week 4 — Secure MCP Server for Ledger
*[Planned]*

### Week 5 — MCP Integration & Advanced Evals
*[Planned]*

### Week 6 — Golden Evals & pgvector
*[Planned]*

### Week 7 — RRF Hybrid Search
*[Planned]*

### Week 8 — Reranking, Deterministic Math & Citations
*[Planned]*

### Week 9 — Observability & Prefix Caching
*[Planned]*

### Week 10 — Idempotent Writes & Injection Defenses
*[Planned]*

### Week 11 — Streaming Responses
*[Planned]*

### Week 12 — Final Polish & System Design Review
*[Planned]*

---

## 4. Technology Stack

| Layer | Technology | Status |
|-------|-----------|--------|
| Language | Python 3.12 | ✓ |
| Schemas | Pydantic v2 | ✓ |
| LLM | OpenAI GPT-4o-mini (via API) | ✓ |
| Testing | pytest | ✓ |
| Eval logging | CSV + Rich tables | ✓ |
| Version control | Git | ✓ |
| Database | PostgreSQL + pgvector | Week 4 |
| MCP | Model Context Protocol server | Week 4 |
| Framework | Manual ReAct → (optional) LangGraph | Week 3 |
| Observability | LangSmith / OpenTelemetry | Week 9 |
| Frontend | SSE streaming | Week 11 |

---

## 5. Design Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-11-10 | Use Pydantic v2 `strict` mode for tool schemas | Eliminates non-conforming tool calls at the API level |
| 2026-11-10 | Temperature 0 as eval default | Eliminates LLM sampling noise for reproducible scores |
| 2026-11-10 | CSV-based eval logging with git SHA | Simple, diffable, tracks regression over time |
| 2026-11-10 | 25 eval cases spanning 6 categories | Covers single, batch, cross-class, comparative, and edge cases |
| 2026-11-10 | Mock prices as static dict | Fully deterministic; swappable in Week 2 |

---

## 6. File Structure

```
e:\AI-Project\
├── .env.example           # Environment template
├── .gitignore
├── Makefile               # make test / make eval / make demo
├── pyproject.toml         # Project metadata & dependencies
├── docs/
│   └── architecture.md    # This document
├── evals/
│   ├── prompts/
│   │   └── eval_cases.py  # 25 eval test cases
│   └── results/
│       └── eval_log.csv   # Cumulative eval scores
├── src/
│   ├── agent/
│   │   ├── llm_client.py  # LLM wrapper with tool-call loop
│   │   └── demo.py        # Interactive demo script
│   ├── evals/
│   │   └── run_eval.py    # Eval runner & scorer
│   └── tools/
│       ├── schemas.py     # Pydantic request/response models
│       └── mock_data.py   # Mock prices & tool execution
└── tests/
    └── test_schemas_and_tools.py
```
