"""Mock LLM adapter.

Produces deterministic responses without making any external API calls.
The adapter simulates a realistic two-phase behaviour:

  Phase 1 — Tool request:
    If the task contains action keywords (search, find, calculate, …) AND
    the agent has a tool whose name matches one of those keywords, the adapter
    returns a ToolCallRequest for that tool.

  Phase 2 — Final response:
    If there is already at least one tool result in the conversation context,
    the adapter synthesises a final answer that references the tool output.
    The same applies when no matching tool is available: a direct answer is
    returned immediately.

This design allows the runner to exercise the full multi-step loop without
any randomness, making the behaviour straightforward to test.
"""

from dataclasses import dataclass

# Keywords that indicate the user wants the agent to *do* something external.
# Mapped to tool-name fragments that would satisfy the intent.
_ACTION_TRIGGERS: dict[str, list[str]] = {
    "search": ["search", "web", "lookup", "query"],
    "find": ["search", "web", "lookup", "query"],
    "look up": ["search", "web", "lookup", "query"],
    "fetch": ["search", "web", "fetch", "http"],
    "calculate": ["calculator", "math", "compute"],
    "compute": ["calculator", "math", "compute"],
    "summarize": ["summarizer", "summary"],
    "summarise": ["summarizer", "summary"],
    "translate": ["translator", "translate"],
    "weather": ["weather", "forecast"],
}


@dataclass(frozen=True)
class FinalResponse:
    text: str


@dataclass(frozen=True)
class ToolCallRequest:
    tool_name: str
    tool_input: str


LLMOutput = FinalResponse | ToolCallRequest


def _find_matching_tool(task_lower: str, available_tools: list[str]) -> str | None:
    """Return the first tool name that matches an action keyword in the task."""
    for keyword, fragments in _ACTION_TRIGGERS.items():
        if keyword in task_lower:
            for tool_name in available_tools:
                tool_lower = tool_name.lower()
                if any(frag in tool_lower for frag in fragments):
                    return tool_name
    return None


def call(
    task: str,
    available_tools: list[str],
    tool_results: list[tuple[str, str]],  # [(tool_name, tool_output), …]
) -> LLMOutput:
    """Return a deterministic mock LLM response.

    Args:
        task:           The original user task (used for keyword matching).
        available_tools: Names of tools assigned to the agent.
        tool_results:   Tool calls already completed in this execution.

    Returns:
        A FinalResponse or a ToolCallRequest.
    """
    # If we already have tool results, synthesise a final answer.
    if tool_results:
        tool_name, tool_output = tool_results[-1]
        return FinalResponse(
            text=(
                f"Based on the result from '{tool_name}': {tool_output}\n\n"
                f"Task completed: {task}"
            )
        )

    # Check if a tool call is warranted.
    if available_tools:
        matched_tool = _find_matching_tool(task.lower(), available_tools)
        if matched_tool:
            return ToolCallRequest(
                tool_name=matched_tool,
                tool_input=task,
            )

    # Default: answer directly without tools.
    return FinalResponse(
        text=f"[Mock response] I have completed the task: {task}"
    )


def execute_tool(tool_name: str, tool_input: str) -> str:
    """Mock tool executor — returns a deterministic string result.

    In production this would dispatch to real tool implementations.
    """
    responses: dict[str, str] = {
        "web-search": f"Search results for '{tool_input}': [result 1, result 2, result 3]",
        "calculator": f"Calculation result for '{tool_input}': 42",
        "summarizer": f"Summary of '{tool_input}': This is a concise summary.",
        "translator": f"Translation of '{tool_input}': [translated text]",
        "weather": f"Weather for '{tool_input}': Sunny, 22°C",
    }

    # Match by fragment so "my-web-search-tool" still gets a sensible response.
    tool_lower = tool_name.lower()
    for key, response in responses.items():
        if key in tool_lower:
            return response

    return f"Tool '{tool_name}' executed with input: {tool_input}. Result: [mock output]"
