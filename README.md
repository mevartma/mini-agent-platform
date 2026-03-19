# Mini Agent Platform

A production-quality, multi-tenant REST API for managing AI agents and tools, running them through a mock LLM pipeline, and storing execution history.

Built with **Python 3.12 · FastAPI · SQLAlchemy 2.0 (async) · PostgreSQL · Alembic · pytest**.

---

## Table of Contents

- [Setup](#setup)
- [Running the Server](#running-the-server)
- [Running Tests](#running-tests)
- [API Reference](#api-reference)
- [Architecture](#architecture)

---

## Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 14+ (running locally or via Docker)

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd mini-agent-platform
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set your database URL:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mini_agent_platform

# Three hardcoded tenant API keys (key:tenant_id pairs, comma-separated)
TENANT_KEYS=key-tenant-alpha:tenant-alpha,key-tenant-beta:tenant-beta,key-tenant-gamma:tenant-gamma
```

### 3. Create the database and run migrations

```bash
# Create the database (if it doesn't exist)
psql -U postgres -c "CREATE DATABASE mini_agent_platform;"

# Apply migrations
alembic upgrade head
```

### Docker alternative

```bash
docker run --name pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:16
psql -U postgres -h localhost -c "CREATE DATABASE mini_agent_platform;"
alembic upgrade head
```

---

## Running the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

Interactive docs (Swagger UI): `http://localhost:8000/docs`

---

## Running Tests

```bash
pytest                    # run all tests
pytest -v                 # verbose output
pytest tests/test_guardrail.py   # single file
pytest --cov=app          # with coverage report
```

All 71 tests run without a database connection — the test suite is fully isolated using mocks.

---

## API Reference

All endpoints (except `/health`) require the `x-api-key` header.

**Available API keys (development defaults):**

| Key | Tenant ID |
|-----|-----------|
| `key-tenant-alpha` | `tenant-alpha` |
| `key-tenant-beta` | `tenant-beta` |
| `key-tenant-gamma` | `tenant-gamma` |

### Health

```bash
curl http://localhost:8000/health
```

---

### Tools

#### Create a tool

```bash
curl -X POST http://localhost:8000/tools \
  -H "x-api-key: key-tenant-alpha" \
  -H "Content-Type: application/json" \
  -d '{"name": "web-search", "description": "Searches the web for information."}'
```

#### List tools (with optional filter)

```bash
# All tools
curl http://localhost:8000/tools \
  -H "x-api-key: key-tenant-alpha"

# Tools assigned to a specific agent
curl "http://localhost:8000/tools?agent_name=Research+Bot" \
  -H "x-api-key: key-tenant-alpha"
```

#### Get, update, delete a tool

```bash
# Get
curl http://localhost:8000/tools/{tool_id} \
  -H "x-api-key: key-tenant-alpha"

# Update (partial)
curl -X PATCH http://localhost:8000/tools/{tool_id} \
  -H "x-api-key: key-tenant-alpha" \
  -H "Content-Type: application/json" \
  -d '{"description": "Updated description."}'

# Delete
curl -X DELETE http://localhost:8000/tools/{tool_id} \
  -H "x-api-key: key-tenant-alpha"
```

---

### Agents

#### Create an agent

```bash
curl -X POST http://localhost:8000/agents \
  -H "x-api-key: key-tenant-alpha" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Research Bot",
    "role": "Researcher",
    "description": "Finds and summarises information on any topic.",
    "tool_ids": ["{tool_id}"]
  }'
```

`tool_ids` is optional — assign tools at creation or later via `PATCH`.

#### List agents (with optional filter)

```bash
# All agents
curl http://localhost:8000/agents \
  -H "x-api-key: key-tenant-alpha"

# Agents that have a specific tool assigned
curl "http://localhost:8000/agents?tool_name=web-search" \
  -H "x-api-key: key-tenant-alpha"
```

#### Get, update, delete an agent

```bash
# Get (returns agent with embedded tools)
curl http://localhost:8000/agents/{agent_id} \
  -H "x-api-key: key-tenant-alpha"

# Update — tool_ids replaces the full tool set (omit to leave unchanged)
curl -X PATCH http://localhost:8000/agents/{agent_id} \
  -H "x-api-key: key-tenant-alpha" \
  -H "Content-Type: application/json" \
  -d '{"role": "Senior Researcher", "tool_ids": ["{tool_id_1}", "{tool_id_2}"]}'

# Delete
curl -X DELETE http://localhost:8000/agents/{agent_id} \
  -H "x-api-key: key-tenant-alpha"
```

---

### Run an Agent

Runs the agent through the mock LLM pipeline and returns the full execution record.

```bash
curl -X POST http://localhost:8000/agents/{agent_id}/run \
  -H "x-api-key: key-tenant-alpha" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Search for the latest developments in quantum computing.",
    "model": "gpt-4o"
  }'
```

**Supported models:** `gpt-4o`, `claude-3-5-sonnet`

**Example response:**

```json
{
  "id": "...",
  "agent_id": "...",
  "tenant_id": "tenant-alpha",
  "model": "gpt-4o",
  "task": "Search for the latest developments in quantum computing.",
  "structured_prompt": "...",
  "final_response": "Based on the result from 'web-search': ...",
  "status": "completed",
  "steps": [
    {
      "step_number": 1,
      "step_type": "tool_call",
      "tool_name": "web-search",
      "tool_input": "Search for the latest...",
      "tool_output": "Search results for '...': [result 1, result 2, result 3]",
      "llm_output": null
    },
    {
      "step_number": 2,
      "step_type": "llm_call",
      "tool_name": null,
      "tool_input": null,
      "tool_output": null,
      "llm_output": "Based on the result from 'web-search': ..."
    }
  ],
  "created_at": "..."
}
```

**Error cases:**
- `400` — prompt injection detected
- `400` — tool not assigned to agent
- `404` — agent not found
- `422` — unsupported model

---

### Execution History

```bash
# Page 1, 20 results per page (defaults)
curl http://localhost:8000/agents/{agent_id}/executions \
  -H "x-api-key: key-tenant-alpha"

# Custom pagination
curl "http://localhost:8000/agents/{agent_id}/executions?page=2&limit=10" \
  -H "x-api-key: key-tenant-alpha"
```

**Response includes:** `items`, `total`, `page`, `limit`, `pages`.

---

## Architecture

### Multi-Tenant Isolation

Every table has a `tenant_id` column. All service-layer functions accept `tenant_id` as a required argument and include it in every query — a request authenticated with `key-tenant-alpha` can never read or modify data belonging to `tenant-beta`, even if it guesses a valid record ID.

API keys are resolved at the FastAPI dependency layer (`app/auth/dependencies.py`) before any route handler runs.

### Execution Pipeline

```
POST /agents/{id}/run
        │
        ▼
  1. Validate model
        │
        ▼
  2. Load agent + tools from DB
        │
        ▼
  3. Guardrail check (regex, deterministic)
        │
        ▼
  4. Build structured prompt
     ┌──────────────────────────┐
     │  SYSTEM INSTRUCTIONS     │
     │  AVAILABLE TOOLS         │
     │  USER INPUT              │
     └──────────────────────────┘
        │
        ▼
  5. Multi-step loop (max 5 iterations)
     ┌─────────────────────────────────────┐
     │  mock_llm.call()                    │
     │    ├─ FinalResponse → exit loop     │
     │    └─ ToolCallRequest               │
     │         ├─ validate tool assigned   │
     │         ├─ execute_tool() (mock)    │
     │         └─ append result, continue  │
     └─────────────────────────────────────┘
        │
        ▼
  6. Persist Execution + ExecutionSteps
        │
        ▼
  7. Return RunResponse
```

If the loop reaches 5 iterations without a `FinalResponse`, the execution is saved with `status: "failed"`.

### Prompt Injection Guardrail

Located in `app/runner/guardrail.py`. Uses 20 compiled regex patterns covering:

| Category | Examples |
|----------|---------|
| Instruction override | `ignore all instructions`, `disregard previous instructions` |
| Role hijacking | `you are now`, `act as`, `pretend to be` |
| System prompt extraction | `reveal your system prompt`, `show me your prompt` |
| Jailbreak keywords | `jailbreak`, `DAN`, `do anything now`, `bypass safety` |
| Delimiter injection | `<system>`, `[INST]`, `### system` |

The check is **deterministic and local** — no LLM calls, no network, O(n) in pattern count.

### Project Structure

```
app/
├── main.py              # FastAPI app, router registration
├── config.py            # Settings (pydantic-settings)
├── auth/
│   ├── tenant_keys.py   # API key → tenant_id map
│   └── dependencies.py  # get_tenant_id FastAPI dependency
├── db/
│   ├── base.py          # DeclarativeBase, TimestampMixin
│   ├── models.py        # ORM models
│   └── session.py       # Async engine + session factory
├── tools/
│   ├── schemas.py
│   ├── service.py
│   └── router.py
├── agents/
│   ├── schemas.py
│   ├── service.py
│   └── router.py
└── runner/
    ├── schemas.py
    ├── guardrail.py
    ├── prompt_builder.py
    ├── mock_llm.py
    ├── service.py
    ├── router.py
    ├── history_schemas.py
    ├── history_service.py
    └── history_router.py
tests/
├── conftest.py
├── test_guardrail.py
├── test_prompt_builder.py
├── test_mock_llm.py
└── test_runner.py
alembic/
└── versions/
    └── ec44ba203b6c_initial.py
```
