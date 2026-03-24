"""SSE streaming version of the agent runner.

Yields SSE-encoded event frames as each step completes, then a final event
once the execution is persisted to the database.
"""

import json
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_uuid
from app.db.models import Execution, ExecutionStep
from app.runner import guardrail, mock_llm, prompt_builder
from app.runner.guardrail import PromptInjectionError
from app.runner.mock_llm import FinalResponse, ToolCallRequest
from app.runner.schemas import SUPPORTED_MODELS, StreamFinalEvent, StreamStepEvent, sse_encode
from app.runner.service import (
    MAX_STEPS,
    AgentNotFoundError,
    ToolNotAssignedError,
    _load_agent,
)


async def run_agent_stream(
    db: AsyncSession,
    tenant_id: str,
    agent_id: str,
    task: str,
    model: str,
) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE frames for each execution step."""

    # ── Validate model ───────────────────────────────────────────────────────
    if model not in SUPPORTED_MODELS:
        yield f"event: error\ndata: {json.dumps({'detail': f'Model {model!r} is not supported.'})}\n\n"
        return

    # ── Load agent ───────────────────────────────────────────────────────────
    try:
        agent = await _load_agent(db, tenant_id, agent_id)
    except AgentNotFoundError as e:
        yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"
        return

    # ── Guardrail ────────────────────────────────────────────────────────────
    try:
        guardrail.check(task)
    except PromptInjectionError as e:
        yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"
        return

    # ── Build prompt & tool list ─────────────────────────────────────────────
    structured_prompt = prompt_builder.build(agent, task)
    available_tool_names = [t.name for t in agent.tools]
    assigned_tool_names = set(available_tool_names)

    # ── Multi-step execution loop ────────────────────────────────────────────
    tool_results: list[tuple[str, str]] = []
    steps: list[dict] = []
    final_response: str | None = None
    status = "completed"

    try:
        for step_number in range(1, MAX_STEPS + 1):
            llm_output = mock_llm.call(task, available_tool_names, tool_results)

            if isinstance(llm_output, FinalResponse):
                final_response = llm_output.text
                step_data: dict = {
                    "step_number": step_number,
                    "step_type": "llm_call",
                    "llm_output": final_response,
                }
                steps.append(step_data)
                yield sse_encode("step", StreamStepEvent(**step_data))
                break

            if isinstance(llm_output, ToolCallRequest):
                if llm_output.tool_name not in assigned_tool_names:
                    raise ToolNotAssignedError(
                        f"Tool '{llm_output.tool_name}' is not assigned to this agent."
                    )

                tool_output = mock_llm.execute_tool(
                    llm_output.tool_name, llm_output.tool_input
                )
                tool_results.append((llm_output.tool_name, tool_output))

                step_data = {
                    "step_number": step_number,
                    "step_type": "tool_call",
                    "tool_name": llm_output.tool_name,
                    "tool_input": llm_output.tool_input,
                    "tool_output": tool_output,
                }
                steps.append(step_data)
                yield sse_encode("step", StreamStepEvent(**step_data))
        else:
            status = "failed"

    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"
        return

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

    for sd in steps:
        db.add(
            ExecutionStep(
                id=new_uuid(),
                execution_id=execution.id,
                **sd,
            )
        )

    await db.commit()

    # ── Yield final event ────────────────────────────────────────────────────
    yield sse_encode(
        "final",
        StreamFinalEvent(
            execution_id=execution.id,
            status=status,
            final_response=final_response,
            total_steps=len(steps),
        ),
    )
