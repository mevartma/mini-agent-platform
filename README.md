![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?logo=python) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi) ![Next.js 15](https://img.shields.io/badge/Next.js-15-black?logo=next.js) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql) ![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis) ![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker) ![License](https://img.shields.io/badge/License-MIT-green)

# Mini Agent Platform

A multi-tenant AI agent management and execution platform. Define agents with assigned tools, run them against tasks via a fully deterministic mock LLM with seven distinct execution scenarios, and observe real-time results through Server-Sent Events streaming. A persistent global chat interface supports `@agent` tagging and parallel execution streams per mention.

The platform ships as a four-service Docker Compose stack — PostgreSQL, Redis, FastAPI backend, and a Next.js frontend — and is ready to run locally in under five minutes.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Quick Start with Docker](#quick-start-with-docker)
  - [First Workspace](#first-workspace)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Mock LLM Scenarios](#mock-llm-scenarios)
- [Chat Interface](#chat-interface)
- [Frontend Pages](#frontend-pages)
- [Development](#development)
  - [Makefile Commands](#makefile-commands)
  - [Running Tests](#running-tests)
  - [Hot Reload](#hot-reload)
- [Database Schema](#database-schema)
- [Authentication](#authentication)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---

## Features

**Agent Management**
- Create, edit, and delete agents with names, descriptions, and system prompts
- Assign multiple tools to each agent; tools are resolved at runtime
- Redis cache-aside for agent and tool reads — no database round-trips on hot paths

**Execution Engine**
- Seven deterministic mock LLM scenarios covering the full spectrum of agentic behavior
- Prompt injection guardrail — 38 patterns blocked before any execution
- Configurable max-steps limit to prevent runaway loops
- All executions and steps persisted to PostgreSQL for audit and replay

**Streaming**
- SSE endpoint (`/agents/{id}/run/stream`) emits typed events: `step`, `final`, `error`
- Steps streamed live as they execute; final event carries the complete execution ID
- Graceful error recovery — stream closes cleanly on failure with an error event

**Chat**
- Global chat sessions per tenant with full message history
- `@AgentName` autocomplete triggers a live SSE execution stream for that agent
- Multiple `@mentions` in one message spawn parallel streams
- Live step-count badge and pulsing indicator per in-flight stream
- Messages persist on stream completion with `agent_name` and `execution_id` linked

**Auth**
- JWT (HS256) with `jti` blacklisting in Redis on logout
- API key authentication for external integrations (header: `x-api-key`)
- Three roles: admin, operator, viewer

**Multi-tenancy**
- Every resource (agents, tools, executions, chat) is scoped to a tenant
- PostgreSQL Row-Level Security enforced via `app.current_tenant_id` session variable
- Tenant registration creates an isolated workspace in one request

---

## Architecture

```
+-------------------------------------------------------------+
|                        Browser                              |
|   Next.js 15 (App Router, React 19, Tailwind v4)           |
|   Pages: login / agents / tools / chat / run / history     |
|   - httpOnly JWT cookie (never exposed to JS)              |
|   - Proxy layer: app/api/* route handlers add Bearer token |
+------------------------+------------------------------------+
                         |
                    HTTP / SSE
                         |
+------------------------v------------------------------------+
|                   FastAPI Backend                           |
|   auth . tenants . agents . tools . runner . chat          |
|   - Pydantic v2 request validation                         |
|   - SQLAlchemy 2.0 async sessions (asyncpg)                |
|   - Redis cache-aside + JWT blacklist                      |
+-----------+------------------------------+------------------+
            |                              |
         asyncpg                       aioredis
            |                              |
+-----------v-----------+   +--------------v-----------------+
|  PostgreSQL 16        |   |  Redis 7                       |
|  - 10 tables          |   |  - jti blacklist (TTL)         |
|  - RLS per tenant     |   |  - agent/tool read cache (TTL) |
+-----------------------+   +--------------------------------+
```

| Layer | Responsibility |
|---|---|
| Browser | Renders UI; never touches JWT directly; sends cookies |
| Next.js proxy | Route handlers read httpOnly cookie, forward to FastAPI with Bearer header |
| FastAPI | Business logic, auth middleware, RBAC, SSE orchestration |
| Mock LLM / Runner | Scenario detection, tool dispatch, step generation |
| PostgreSQL | Persistent state — all tenant-scoped resources and executions |
| Redis | Ephemeral state — JWT blacklist and hot-path read cache |

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Backend language | Python | 3.12 |
| API framework | FastAPI | 0.115 |
| ORM | SQLAlchemy (async) | 2.0 |
| DB driver | asyncpg | latest |
| Migrations | Alembic | latest |
| Password hashing | bcrypt | latest |
| JWT | PyJWT | latest |
| Frontend framework | Next.js (App Router) | 15 |
| UI library | React | 19 |
| Language | TypeScript (strict) | 5 |
| Styling | Tailwind CSS | v4 |
| Database | PostgreSQL | 16 |
| Cache / blacklist | Redis | 7 |
| Containerization | Docker Compose | v2 |

---

## Getting Started

### Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)
- GNU Make
- Git

No local Python or Node.js installation is required — everything runs inside containers.

### Quick Start with Docker

```bash
# 1. Clone the repository
git clone https://github.com/your-org/mini-agent-platform.git
cd mini-agent-platform

# 2. Create environment file
cp .env.example .env
# Edit .env and set a strong JWT_SECRET before continuing

# 3. Build and start all four services
make up

# 4. Run database migrations
make migrate

# 5. Open the application
open http://localhost:3000
```

Services started by `make up`:

| Service | Port | Description |
|---|---|---|
| `frontend` | 3000 | Next.js dev server |
| `api` | 8000 | FastAPI (uvicorn --reload) |
| `db` | 5432 | PostgreSQL 16 |
| `cache` | 6379 | Redis 7 |

### First Workspace

1. Navigate to `http://localhost:3000/register`
2. Fill in your workspace name, email, and password — this creates an isolated tenant
3. You are redirected to `/login`; sign in with the credentials you just created
4. You will land on the agents list — your workspace is empty and ready

To create your first agent:

1. Go to **Agents → New Agent**
2. Enter a name, optional description, and a system prompt
3. Optionally assign tools from the tools list (create tools first at **Tools → New Tool**)
4. Save — then click **Run** to execute your first task

---

## Configuration

All variables are read at startup via Pydantic settings from `.env` (local) or `.env.docker` (container).

| Variable | Type | Required | Default | Description |
|---|---|---|---|---|
| `DATABASE_URL` | string | yes | — | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | string | yes | — | `redis://host:6379` |
| `JWT_SECRET` | string | yes | — | HMAC-SHA256 signing secret. **Change before deploying.** |
| `JWT_EXPIRE_MINUTES` | integer | no | `60` | Token lifetime in minutes |

Minimal `.env` example:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/miniagent
REDIS_URL=redis://localhost:6379
JWT_SECRET=change-me-in-production
JWT_EXPIRE_MINUTES=60
```

---

## API Reference

All endpoints require `Authorization: Bearer <token>` unless marked **public**. Alternatively, pass `x-api-key: map_<prefix>_<secret>` for API key auth.

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/login` | public | Exchange email + password for JWT |
| `POST` | `/auth/logout` | JWT | Blacklist current `jti` in Redis |

### Tenants

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/tenants/register` | public | Create new tenant + admin user |
| `POST` | `/tenants/api-keys` | JWT | Generate a new API key |
| `GET` | `/tenants/api-keys` | JWT | List API keys for tenant |
| `DELETE` | `/tenants/api-keys` | JWT | Revoke an API key |

### Agents

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/agents` | JWT | Create agent |
| `GET` | `/agents` | JWT | List agents for tenant |
| `GET` | `/agents/{id}` | JWT | Get agent by ID |
| `PATCH` | `/agents/{id}` | JWT | Update agent fields |
| `DELETE` | `/agents/{id}` | JWT | Delete agent |

### Tools

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/tools` | JWT | Create tool |
| `GET` | `/tools` | JWT | List tools for tenant |
| `GET` | `/tools/{id}` | JWT | Get tool by ID |
| `PATCH` | `/tools/{id}` | JWT | Update tool |
| `DELETE` | `/tools/{id}` | JWT | Delete tool |

### Runner

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/agents/{id}/run` | JWT | Blocking execution — returns full result |
| `POST` | `/agents/{id}/run/stream` | JWT | Streaming execution — SSE `text/event-stream` |
| `GET` | `/agents/{id}/executions` | JWT | Paginated execution history |

### Chat

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/chat` | JWT | Create a chat session |
| `GET` | `/chat` | JWT | List chat sessions for tenant |
| `GET` | `/chat/{id}/messages` | JWT | Get messages in a session |
| `POST` | `/chat/{id}/messages` | JWT | Post a message (triggers agent run if `@mention`) |

### Health

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | public | Returns `{"status": "ok"}` |

### SSE Streaming — Event Schema

Connect with a `POST` to `/agents/{id}/run/stream`, body `{"task": "your task here"}`.

```bash
curl -N -X POST http://localhost:8000/agents/<id>/run/stream \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"task": "search and summarize recent news"}'
```

**`step` event** — emitted for each execution step:

```
event: step
data: {"step_number": 1, "step_type": "tool_call", "tool_name": "web_search", "tool_input": {"query": "recent news"}, "tool_output": {"result": "..."}, "llm_output": null}
```

**`final` event** — emitted once when execution completes:

```
event: final
data: {"execution_id": "uuid", "status": "completed", "final_response": "Here is a summary of recent news...", "total_steps": 3}
```

**`error` event** — emitted on unrecoverable failure:

```
event: error
data: {"detail": "Agent not found or execution failed"}
```

---

## Mock LLM Scenarios

No external API calls are made. The runner detects the scenario from the task string at execution time. All steps are deterministic.

| Scenario | Trigger Keywords | Step Count | Description |
|---|---|---|---|
| `direct` | "what is", "explain", "define", "describe" | 1 | Single LLM call, no tools invoked |
| `single_tool` | task keyword matches an available tool name | 2 | One tool call followed by LLM synthesis |
| `multi_tool` | "search and summarize", "find and translate" | 3 | Two sequential tool calls, final synthesis |
| `tool_failure` | "broken tool", "unavailable service" | 2 | Tool raises error; LLM degrades gracefully |
| `retry` | "retry", "keep trying", "try again" | 3 | Tool fails on first attempt, retries, succeeds |
| `multi_step` | "step by step", "analyze", "reason through" | 4 | Three reasoning phases (PLANNING → ANALYSIS → SYNTHESIS) + final |
| `research_pipeline` | "deep research", "research and translate" | 4 | Three-tool chain: search → summarize → translate, then final |

Scenario detection runs in order; first match wins. If no trigger matches and no tool names appear in the task, the `direct` scenario is used as fallback.

---

## Chat Interface

### How @Mentions Work

Type `@` in the chat input to open an autocomplete dropdown of available agents. Select an agent (or type its name) to tag it. You can mention multiple agents in a single message.

When the message is sent:

1. The frontend identifies all `@AgentName` tokens in the message
2. One SSE stream is opened per mentioned agent, in parallel
3. Each stream renders its execution steps inline in the message thread as they arrive
4. A pulsing indicator appears next to each in-flight stream; a step-count badge shows progress
5. When all streams complete, their `final_response` values are committed as agent messages with linked `execution_id`

### Message Persistence

Messages with role `user` are stored immediately on send. Messages with role `agent` are written once the SSE stream emits its `final` event. Each agent message carries `agent_name` and `execution_id` for traceability.

### Parallel Streams Example

```
User: @Researcher find competitors, @Translator translate to Hebrew

  [Researcher stream]  step 1/3 ... step 2/3 ... step 3/3 -> final
  [Translator stream]  step 1/2 ... step 2/2 -> final
```

Both streams run concurrently; the chat UI renders both step sequences simultaneously.

---

## Frontend Pages

| Path | Type | Description |
|---|---|---|
| `/login` | public | Email + password login form |
| `/register` | public | Tenant registration (workspace name, email, password) |
| `/agents` | protected | List all agents; links to edit, run, history |
| `/agents/new` | protected | Create new agent form with tool assignment |
| `/agents/{id}/edit` | protected | Edit agent name, description, prompt, tools |
| `/agents/{id}/run` | protected | Run form; blocking execution with live ExecutionSteps display |
| `/agents/{id}/history` | protected | Paginated execution history with step drill-down |
| `/tools` | protected | List all tools |
| `/tools/new` | protected | Create new tool |
| `/tools/{id}/edit` | protected | Edit tool name and description |
| `/chat` | protected | Global chat — `@mention` agents, parallel SSE streams |

---

## Development

### Makefile Commands

| Command | Description |
|---|---|
| `make up` | Build images and start all four services |
| `make down` | Stop and remove containers |
| `make logs` | Tail logs from all services |
| `make logs s=api` | Tail logs from the `api` service only |
| `make migrate` | Run pending Alembic migrations inside the `api` container |
| `make test` | Run the full pytest suite (71 tests) |
| `make test args="-k test_runner"` | Run a filtered subset of tests |
| `make shell-api` | Open a bash shell inside the `api` container |
| `make shell-frontend` | Open a bash shell inside the `frontend` container |
| `make build` | Rebuild images without starting containers |

### Running Tests

```bash
# All tests
make test

# Single module
make test args="-k test_mock_llm"

# With verbose output
make test args="-v"

# With coverage
make test args="--cov=app --cov-report=term-missing"
```

Test modules:

| Module | Tests | Covers |
|---|---|---|
| `test_mock_llm.py` | scenario detection, `execute_tool` output formatting | Mock LLM |
| `test_runner.py` | orchestration, guardrail enforcement, tool validation, max-steps limit | Runner |
| `test_prompt_builder.py` | prompt structure, sections, tool injection | Prompt builder |
| `test_guardrail.py` | 38 prompt injection patterns | Guardrail |

### Hot Reload

- **Backend**: `uvicorn --reload` watches `app/` — any `.py` change restarts the server automatically
- **Frontend**: Next.js dev server with `WATCHPACK_POLLING=true` set in `docker-compose.yml` for compatibility inside Docker on macOS and Windows

No manual restart is needed during development. Changes take effect within 1–2 seconds.

---

## Database Schema

| Table | Purpose | Key Columns | RLS |
|---|---|---|---|
| `tenants` | Isolated workspaces | `id`, `name`, `created_at` | no |
| `users` | Tenant members with roles | `id`, `tenant_id`, `email`, `hashed_password`, `role` | yes |
| `api_keys` | External API credentials | `id`, `tenant_id`, `prefix`, `hashed_secret`, `created_at` | yes |
| `tools` | Reusable tool definitions | `id`, `tenant_id`, `name`, `description` | yes |
| `agents` | Agent definitions with prompts | `id`, `tenant_id`, `name`, `description`, `system_prompt` | yes |
| `agent_tools` | Many-to-many agent to tool | `agent_id`, `tool_id` | yes |
| `executions` | Execution records | `id`, `agent_id`, `tenant_id`, `task`, `status`, `final_response` | yes |
| `execution_steps` | Individual steps per execution | `id`, `execution_id`, `step_number`, `step_type`, `tool_name`, `tool_input`, `tool_output`, `llm_output` | yes |
| `chat_sessions` | Chat session containers | `id`, `tenant_id`, `created_at` | yes |
| `chat_messages` | Messages within a session | `id`, `session_id`, `role`, `content`, `agent_name`, `execution_id` | yes |

RLS is enforced by setting `app.current_tenant_id` as a PostgreSQL session variable at the start of each request. Tables marked "yes" above have policies that restrict all operations to rows matching the current tenant.

---

## Authentication

### JWT Flow

```
POST /auth/login
  -> {access_token, token_type}

Authorization: Bearer <token>  (all protected routes)
  -> Middleware decodes token, extracts tenant_id + user_id + role
  -> Sets app.current_tenant_id for RLS

POST /auth/logout
  -> jti added to Redis blacklist with TTL = remaining token lifetime
  -> Token rejected on all subsequent requests
```

Tokens use HS256 and carry a `jti` (JWT ID) claim. On each request the `jti` is checked against Redis before proceeding. Blacklisted tokens are rejected even if not yet expired.

### API Key Format

```
x-api-key: map_<prefix>_<secret>
```

- `prefix` — stored in plain text for lookup
- `secret` — bcrypt-hashed in `api_keys.hashed_secret`
- Resolved to a tenant and role on each request; the same RBAC rules apply

### RBAC Roles

| Role | Agents | Tools | Run | History | Tenants | Users |
|---|---|---|---|---|---|---|
| `admin` | CRUD | CRUD | yes | yes | manage | manage |
| `operator` | read + write | read + write | yes | yes | no | no |
| `viewer` | read | read | no | yes | no | no |

---

## Project Structure

```
mini-agent-platform/
├── app/                        # FastAPI backend
│   ├── main.py                 # App factory, router registration, middleware
│   ├── config.py               # Pydantic settings (reads .env)
│   ├── auth/
│   │   ├── dependencies.py     # get_current_user, require_role
│   │   ├── jwt.py              # Token creation and verification
│   │   ├── rbac.py             # Role permission constants
│   │   └── router.py           # /auth/login, /auth/logout
│   ├── tenants/                # Tenant registration + API key management
│   ├── agents/                 # Agent CRUD + Redis cache-aside
│   ├── tools/                  # Tool CRUD + Redis cache-aside
│   ├── runner/
│   │   ├── router.py           # /agents/{id}/run + /run/stream
│   │   ├── history_router.py   # /agents/{id}/executions
│   │   ├── mock_llm.py         # 7-scenario deterministic LLM
│   │   ├── orchestrator.py     # Step loop, guardrail, tool dispatch
│   │   └── prompt_builder.py   # System + tool prompt assembly
│   ├── chat/                   # Chat sessions and messages
│   ├── cache/                  # Redis client, key helpers, cache ops
│   └── db/
│       ├── models.py           # SQLAlchemy ORM models (all 10 tables)
│       ├── session.py          # Async engine + session factory
│       └── base.py             # DeclarativeBase
├── frontend/
│   ├── app/
│   │   ├── (dashboard)/        # Protected routes (agents, tools, chat)
│   │   ├── login/              # Login page
│   │   ├── register/           # Tenant registration page
│   │   └── api/                # Next.js proxy route handlers
│   ├── components/             # Sidebar, AgentForm, ToolForm, ChatInput,
│   │                           #   ChatMessage, ExecutionSteps
│   ├── lib/
│   │   ├── api.ts              # Server-side apiFetch with cookie -> Bearer
│   │   ├── types.ts            # Shared TypeScript types
│   │   └── middleware.ts       # Auth redirect middleware
│   └── public/
├── alembic/
│   └── versions/               # 4 migrations
├── tests/                      # pytest (71 tests)
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
└── .env.example
```

---

## Contributing

1. Fork the repository and create a feature branch from `main`
2. Follow existing conventions: snake_case for Python, camelCase for TypeScript, kebab-case for files
3. Add or update tests for any changed behavior — the suite must remain green (`make test`)
4. Keep PRs focused: one concern per pull request
5. Run `make up && make migrate && make test` before opening a PR to verify the full stack

---

## License

This project is licensed under the [MIT License](LICENSE).
