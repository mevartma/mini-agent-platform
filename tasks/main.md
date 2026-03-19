# AI Coding Exercise — Mini Agent Platform

## What is an Agent Platform?

An Agent Platform is a system that manages "AI agents" — configurable entities that can perform tasks using various tools and instructions.

Each Agent has:

- A **name**, **role**, and **description** (e.g., "Analyzer Agent, a research assistant who analyzes data").
- A set of **Tools** it can use (like "web-search" or "summarizer").
- The ability to **run a task** by generating a prompt and passing it to an LLM (e.g. "summarize the last Q2 report that was published").

Your task is to build a small, backend-only version of such a platform.

---

## Goal

Build a small Agent Platform that can:

1. Create and manage **Agents** (name, role, description, tools).
2. Create and manage **Tools** (name, description).
3. **Run agents** through a mock AI prompt pipeline — generate a final prompt and simulate an LLM response.

> **Important:** the platform must support multiple tenants. Each tenant's data must be fully isolated in the database using a `tenant_id` column.

---

## Core Features

### Agent CRUD

- Create, read, update, and delete agents.
- Each agent includes `name`, `role`, `description`, and a list of `tools`.
- Retrieve agents with optional filters: e.g., filter by tool name.

### Tool CRUD

- Create, read, update, and delete tools.
- Each tool includes `name` and `description`.
- Retrieve tools with optional filters: e.g., filter by agent name.

### Run Agent

Run the agent with **input** (task) and **model**.

- For model, you can define a predefined list of supported models, for example: `["gpt-4o"]`.

**Prompt-injection guardrail:**

- Add a basic prompt-injection guardrail.
- The protection should use a simple heuristic, such as string matching or regular expressions.
- The check must be deterministic and local (no additional LLM calls or external services).
- The goal is to demonstrate awareness — not to build a production-grade security system.

**The system should:**

1. Load the relevant information about the agent (name, role, description, assigned tools).
2. Create the final prompt based on the agent's configuration and the user input. The prompt must have a clear structure and separation between:
   - System instructions
   - Tool descriptions
   - User input
3. Call a **mock LLM adapter** (no real external API calls).
   - The adapter should return deterministic responses.
   - It may return either:
     - A **final response**
     - A **request to call** one of the agent's tools

**Multi-step execution:**

- The mock LLM may deterministically decide to request tool calls based on the task and existing context, and should be re-invoked after each tool execution until a final response is returned.
- If the mock LLM requests a tool call:
  1. Validate that the tool is assigned to the agent.
  2. Execute the tool (tool implementations may also be mocked — no real external integrations required).
  3. Append the tool result to the conversation context.
  4. Continue the interaction until a final response is produced.
- Implement a **safeguard to prevent infinite execution loops**.
- Store **execution history** (including structured prompt, model, tool calls, final response, timestamp).

### Run Agent History

- Retrieve the agent executions.
- Implement **pagination** for large result sets.

### API Authentication (Multi-Tenant)

- For simplicity, define a few hardcoded API keys, each representing a different tenant.
- Each API request must include the API key in the header.

---

## Deliverables

- A working API project in **Python or TypeScript** (no frontend required).
- Database migrations and schema setup.
- Unit tests for main logic.
- A clear **README** explaining how to run, test, and call the API.

### Evaluation Criteria

In addition to correctness, we evaluate:

- Code organization and readability
- Design decisions and separation of responsibilities
- Maintainability and extensibility

> Assume this code will be owned by a team and maintained over time. Treat this as **production-quality code**, not a POC.
