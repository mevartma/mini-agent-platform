"""Agent runner service.

Orchestrates the full execution pipeline:
  1. Validate the model and load the agent.
  2. Run the prompt injection guardrail.
  3. Build the structured prompt.
  4. Enter the multi-step LLM loop (capped at MAX_STEPS).
  5. Persist the Execution and all ExecutionStep records.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import new_uuid
from app.db.models import Agent, AgentTool, Execution, ExecutionStep
from app.runner import guardrail, mock_llm, prompt_builder
from app.runner.guardrail import PromptInjectionError
from app.runner.mock_llm import FinalResponse, ToolCallRequest
from app.runner.schemas import SUPPORTED_MODELS

MAX_STEPS = 5


class AgentNotFoundError(Exception):
    pass


class UnsupportedModelError(Exception):
    pass


class ToolNotAssignedError(Exception):
    pass


async def _load_agent(db: AsyncSession, tenant_id: str, agent_id: str) -> Agent:
    agent = await db.scalar(
        select(Agent)
        .options(selectinload(Agent.agent_tools).selectinload(AgentTool.tool))
        .where(Agent.tenant_id == tenant_id, Agent.id == agent_id)
    )
    if not agent:
        raise AgentNotFoundError(f"Agent '{agent_id}' not found.")
    return agent


async def run_agent(
    db: AsyncSession,
    tenant_id: str,
    agent_id: str,
    task: str,
    model: str,
) -> Execution:
    # ── Validate model ───────────────────────────────────────────────────────
    if model not in SUPPORTED_MODELS:
        raise UnsupportedModelError(
            f"Model '{model}' is not supported. Choose from: {SUPPORTED_MODELS}"
        )

    # ── Load agent ───────────────────────────────────────────────────────────
    agent = await _load_agent(db, tenant_id, agent_id)

    # ── Guardrail ────────────────────────────────────────────────────────────
    guardrail.check(task)  # raises PromptInjectionError if detected

    # ── Build initial prompt ─────────────────────────────────────────────────
    structured_prompt = prompt_builder.build(agent, task)
    available_tool_names = [t.name for t in agent.tools]
    assigned_tool_names = set(available_tool_names)

    # ── Multi-step execution loop ────────────────────────────────────────────
    tool_results: list[tuple[str, str]] = []
    steps: list[dict] = []
    final_response: str | None = None
    status = "completed"

    for step_number in range(1, MAX_STEPS + 1):
        llm_output = mock_llm.call(task, available_tool_names, tool_results)

        if isinstance(llm_output, FinalResponse):
            final_response = llm_output.text
            steps.append(
                {
                    "step_number": step_number,
                    "step_type": "llm_call",
                    "llm_output": final_response,
                }
            )
            break

        if isinstance(llm_output, ToolCallRequest):
            # Validate the tool is actually assigned to this agent.
            if llm_output.tool_name not in assigned_tool_names:
                raise ToolNotAssignedError(
                    f"Tool '{llm_output.tool_name}' is not assigned to this agent."
                )

            tool_output = mock_llm.execute_tool(
                llm_output.tool_name, llm_output.tool_input
            )
            tool_results.append((llm_output.tool_name, tool_output))

            steps.append(
                {
                    "step_number": step_number,
                    "step_type": "tool_call",
                    "tool_name": llm_output.tool_name,
                    "tool_input": llm_output.tool_input,
                    "tool_output": tool_output,
                }
            )
    else:
        # Loop exhausted without a FinalResponse.
        status = "failed"
        final_response = None

    # ── Persist execution ────────────────────────────────────────────────────
    execution = Execution(
        id=new_uuid(),
        tenant_id=tenant_id,
        agent_id=agent_id,
        model=model,
        task=task,
        structured_prompt=structured_prompt,
        final_response=final_response,
        status=status,
    )
    db.add(execution)
    await db.flush()

    for step_data in steps:
        db.add(
            ExecutionStep(
                id=new_uuid(),
                execution_id=execution.id,
                **step_data,
            )
        )

    await db.commit()

    # Reload with steps for the response.
    await db.refresh(execution)
    result = await db.scalar(
        select(Execution)
        .options(selectinload(Execution.steps))
        .where(Execution.id == execution.id)
    )
    return result  # type: ignore[return-value]
