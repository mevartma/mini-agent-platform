# Plan: SSE Streaming, Rich Scenarios, and Global Agent Chat

status: approved
created: 2026-03-24
approved: 2026-03-24
estimated_phases: 4
phases_done: [1, 2, 3, 4]

## Goal
Stream agent executions over SSE, expand the mock LLM with 7 rich deterministic scenarios, add a persisted global chat interface where users type @AgentName to invoke agents in parallel, with each agent's execution steps appearing in real time.

## Architecture Decisions
- **SSE transport**: `POST /agents/{id}/run/stream` → `StreamingResponse(media_type="text/event-stream")`; three event types: `step`, `final`, `error`
- **Chat model**: `ChatSession` + `ChatMessage`; messages have role `user` or `agent`; agent messages link to an `execution_id`
- **Multi-agent parallel**: frontend parses all `@Name` mentions, opens one SSE fetch stream per agent simultaneously, interleaves events in chat order
- **Scenario detection**: pure keyword matching in `mock_llm.py` — no new API fields

---

## Phase 1: Rich Mock LLM Scenarios
- **Files to read**: `app/runner/mock_llm.py`, `app/runner/service.py`
- **Files to modify**: `app/runner/mock_llm.py`
- **Tasks**:
  1. Add `detect_scenario(task, tools) -> str` returning one of 7 scenario keys
  2. Implement all 7 scenarios in `call()`:
     - `direct` — no tool; 1 LLM call with a rich multi-sentence answer. Keywords: "what is", "explain", "who is", "define"
     - `single_tool` — 1 tool call + 1 LLM synthesis. Keywords: "search", "find", "calculate", "weather"
     - `multi_tool` — tool A → intermediate LLM reasoning → tool B → final synthesis (3 steps). Keywords: "search and summarize", "find and translate"
     - `tool_failure` — tool call returns an error string → LLM gracefully acknowledges failure and provides partial answer. Keywords: "broken", "unavailable", "offline"
     - `multi_step` — 3 LLM reasoning rounds (planning → analysis → synthesis) before final answer. Keywords: "step by step", "analyze", "reason through", "evaluate"
     - `research_pipeline` — web-search → summarizer → translator → final LLM answer (4 steps). Keywords: "deep research", "research and translate"
     - `retry` — tool fails on first call, succeeds on retry, LLM synthesises. Keywords: "retry", "keep trying", "try again"
  3. Enrich `execute_tool()` responses: return 3–5 sentence realistic mock payloads per tool type; tool_failure scenario returns `"ERROR: service unavailable (timeout after 30s)"`
  4. Enrich `FinalResponse.text` per scenario: detailed 2–4 sentence answers that reference tool outputs by name
- **Acceptance criteria**: each scenario keyword triggers the correct step count; `make test` still passes; tool_failure produces 2 steps with error text visible
- **Estimated effort**: medium

## Phase 2: Backend SSE Streaming Endpoint
- **Files to read**: `app/runner/service.py`, `app/runner/router.py`, `app/runner/schemas.py`, `app/db/session.py`
- **Files to modify**: `app/runner/router.py`, `app/runner/schemas.py`
- **Files to create**: `app/runner/stream_service.py`
- **Tasks**:
  1. Add to `schemas.py`: `StreamStepEvent(step_type, step_number, tool_name, tool_input, tool_output, llm_output)` and `StreamFinalEvent(execution_id, status, final_response, total_steps)` Pydantic models; `sse_encode(event, data)` helper that formats `event: <type>\ndata: <json>\n\n`
  2. `stream_service.py`: `run_agent_stream()` async generator — clones `run_agent()` logic but `yield`s `sse_encode("step", step_event)` after each iteration; yields `sse_encode("final", final_event)` on success or `sse_encode("error", {"detail": str(e)})` on exception; uses same `get_db_for_tenant` session lifecycle; DB writes happen identically to `run_agent()`
  3. Add `POST /agents/{id}/run/stream` route to `router.py`; returns `StreamingResponse(run_agent_stream(...), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})`; same RBAC guard (`EXECUTIONS_RUN`)
- **Acceptance criteria**: `curl -N -X POST /agents/{id}/run/stream -H "Authorization: Bearer $TOKEN" -d '{"task":"search for AI news","model":"gpt-4o"}' | cat` prints SSE lines one-by-one; execution record exists in DB after stream ends; all 7 scenarios stream correctly
- **Estimated effort**: high

## Phase 3: Chat Session DB + API
- **Files to read**: `app/db/models.py`, `app/db/base.py`
- **Files to modify**: `app/db/models.py`, `app/main.py`
- **Files to create**: `alembic/versions/004_chat.py`, `app/chat/__init__.py`, `app/chat/schemas.py`, `app/chat/service.py`, `app/chat/router.py`
- **Tasks**:
  1. Add `ChatSession` model: `id`, `tenant_id` (FK→tenants), `name`, `created_at`, `updated_at`
  2. Add `ChatMessage` model: `id`, `session_id` (FK→chat_sessions), `tenant_id`, `role` (enum: `user`|`agent`), `content`, `agent_name` (nullable), `execution_id` (nullable, FK→executions), `created_at`
  3. Migration `004_chat.py`: create both tables with indexes on `session_id`, `tenant_id`
  4. `schemas.py`: `SessionCreate`, `SessionResponse`, `MessageCreate`, `MessageResponse`
  5. `service.py`: `create_session`, `list_sessions`, `get_session`, `list_messages`, `add_message`
  6. `router.py`: `POST /chat` (create session), `GET /chat` (list sessions), `GET /chat/{id}/messages` (list messages, newest-first, paginated), `POST /chat/{id}/messages` (add message, returns saved `MessageResponse`)
  7. Register router in `main.py`
- **Acceptance criteria**: `POST /chat` creates a session; `POST /chat/{id}/messages` with role `user` saves and returns message; `GET /chat/{id}/messages` returns paginated list
- **Estimated effort**: medium

## Phase 4: Frontend Global Chat UI
- **Files to read**: `frontend/app/(dashboard)/agents/page.tsx`, `frontend/components/Sidebar.tsx`
- **Files to modify**: `frontend/components/Sidebar.tsx`, `frontend/lib/types.ts`
- **Files to create**:
  - `frontend/app/(dashboard)/chat/page.tsx` — chat page
  - `frontend/app/api/chat/route.ts` — proxy: POST (create session), GET (list sessions)
  - `frontend/app/api/chat/[id]/messages/route.ts` — proxy: GET (list), POST (add)
  - `frontend/app/api/agents/[id]/run/stream/route.ts` — SSE proxy (pipes FastAPI stream to browser)
  - `frontend/components/ChatMessage.tsx` — renders one message bubble (user or agent with live steps)
  - `frontend/components/ChatInput.tsx` — textarea with @mention autocomplete dropdown
- **Tasks**:
  1. Add "Chat" nav item to `Sidebar.tsx` linking to `/chat`
  2. `ChatInput.tsx`: textarea that detects `@` typing, shows autocomplete dropdown of agent names (loaded from `GET /agents`), inserts `@AgentName` tag on select; submits on Enter (Shift+Enter for newline)
  3. `ChatMessage.tsx`: user bubbles on the right; agent bubbles on the left with robot emoji, agent name, timestamp; agent bubbles render `ExecutionSteps` live during streaming; show pulsing dot while stream is open; show final response text when `final` event arrives
  4. `ChatPage.tsx`: on mount, load or create a default session; load message history; render `ChatMessage` list scrolled to bottom; wire up `ChatInput`
  5. On message submit: (a) POST user message to `/api/chat/{id}/messages`; (b) parse all `@AgentName` mentions → resolve to agent IDs; (c) for each agent, open a parallel `fetch` SSE stream to `/api/agents/{agentId}/run/stream`; (d) render streaming steps live; (e) on `final` event, POST agent message to `/api/chat/{id}/messages` with `execution_id`
  6. SSE proxy `run/stream/route.ts`: forward POST body to FastAPI, pipe `ReadableStream` body back without buffering (`transferEncoding: chunked`)
  7. Update `lib/types.ts`: add `ChatSession`, `ChatMessage`, `StreamStepEvent`, `StreamFinalEvent` types
- **Acceptance criteria**: typing `@ResearchBot analyze AI trends step by step` triggers multi_step scenario; steps appear one by one in the bubble; tagging two agents simultaneously shows both bubbles streaming in parallel; messages survive page refresh
- **Estimated effort**: high

---

## Dependencies
- Phase 1 is fully independent
- Phase 2 is fully independent (but Phase 4 depends on it)
- Phase 3 is fully independent (but Phase 4 depends on it)
- Phase 4 requires Phases 2 and 3 to be complete

## Risks
- FastAPI `StreamingResponse` + asyncpg: the async generator holds a DB session open for the full stream duration — session must not be closed before the generator is exhausted
- Next.js route handler SSE proxy: must set `headers: { "Content-Type": "text/event-stream" }` and NOT buffer the body; `Response` from a `ReadableStream` works; `NextResponse` may buffer
- Parallel SSE streams in frontend: each stream is an independent `fetch` — no coordination needed, but React state updates from multiple concurrent streams must use functional `setState` to avoid stale closures
- @mention autocomplete: agents list must be pre-loaded before the user starts typing; debounce is not needed since the list is local
