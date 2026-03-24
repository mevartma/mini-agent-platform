"""Mock LLM adapter — 7 deterministic simulation scenarios.

Scenarios (detected from task keywords, evaluated in priority order):

  research_pipeline — 3-tool chain: web-search → summarizer → translator → LLM synthesis
  retry             — tool fails on first attempt, LLM retries, succeeds on second
  tool_failure      — tool fails, LLM gracefully degrades to partial answer
  multi_tool        — two different tools called sequentially, combined synthesis
  multi_step        — 3 reasoning phases (PLANNING → ANALYSIS → SYNTHESIS) via tool
  direct            — single LLM answer, no tool calls
  single_tool       — one tool call then LLM synthesis (default when a tool matches)

No external API calls are made. All responses are deterministic.
"""

from dataclasses import dataclass

# ── Sentinel prefixes injected into tool_input to control execute_tool ─────
_FAIL_SENTINEL = "__FAIL__:"
_RETRY_SENTINEL = "__RETRY__:"
_PHASE_PREFIX = "__PHASE__:"  # __PHASE__:PLANNING:actual task


# ── Response types ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FinalResponse:
    text: str


@dataclass(frozen=True)
class ToolCallRequest:
    tool_name: str
    tool_input: str


LLMOutput = FinalResponse | ToolCallRequest


# ── Scenario detection ──────────────────────────────────────────────────────

_SCENARIO_TRIGGERS: list[tuple[str, list[str]]] = [
    (
        "research_pipeline",
        ["deep research", "research and translate", "comprehensive research", "full research pipeline"],
    ),
    (
        "retry",
        ["retry", "keep trying", "try again", "attempt again", "reattempt"],
    ),
    (
        "tool_failure",
        ["broken tool", "unavailable service", "offline tool", "simulate failure", "trigger error"],
    ),
    (
        "multi_tool",
        [
            "search and summarize", "find and translate", "search and translate",
            "look up and summarize", "fetch and summarize", "search then translate",
        ],
    ),
    (
        "multi_step",
        [
            "step by step", "reason through", "think through", "deep analysis",
            "evaluate and compare", "analyse in depth", "analyze in depth",
            "structured analysis", "detailed breakdown",
        ],
    ),
    (
        "direct",
        [
            "what is ", "explain ", "who is ", "define ", "describe ",
            "tell me about", "give me a summary of", "what are ",
        ],
    ),
]


def _detect_scenario(task_lower: str, available_tools: list[str]) -> str:
    # High-priority multi-step scenarios checked first
    high_priority = {"research_pipeline", "retry", "tool_failure", "multi_tool", "multi_step"}
    for scenario, triggers in _SCENARIO_TRIGGERS:
        if scenario in high_priority and any(trigger in task_lower for trigger in triggers):
            return scenario
    # Tool resolution beats generic direct keywords
    if available_tools and _find_tool_for_task(task_lower, available_tools):
        return "single_tool"
    # Finally, keyword-based direct
    for scenario, triggers in _SCENARIO_TRIGGERS:
        if scenario not in high_priority and any(trigger in task_lower for trigger in triggers):
            return scenario
    return "direct"


# ── Tool resolution helpers ─────────────────────────────────────────────────

_ACTION_TRIGGERS: dict[str, list[str]] = {
    "search":    ["search", "web", "lookup", "query"],
    "find":      ["search", "web", "lookup", "query"],
    "look up":   ["search", "web", "lookup", "query"],
    "fetch":     ["search", "web", "fetch", "http"],
    "calculate": ["calculator", "math", "compute"],
    "compute":   ["calculator", "math", "compute"],
    "summarize": ["summarizer", "summary"],
    "summarise": ["summarizer", "summary"],
    "translate": ["translator", "translate"],
    "weather":   ["weather", "forecast"],
    "analyze":   ["analyzer", "analysis", "search", "web"],
    "analyse":   ["analyzer", "analysis", "search", "web"],
    "research":  ["search", "web", "research"],
}


def _find_tool_for_task(task_lower: str, available_tools: list[str]) -> str | None:
    """Return the first tool whose name matches an action keyword in the task."""
    for keyword, fragments in _ACTION_TRIGGERS.items():
        if keyword in task_lower:
            for tool_name in available_tools:
                if any(frag in tool_name.lower() for frag in fragments):
                    return tool_name
    return None


def _find_tool_by_type(available_tools: list[str], fragments: list[str]) -> str | None:
    """Return the first tool whose name contains any of the given fragments."""
    for tool_name in available_tools:
        if any(frag in tool_name.lower() for frag in fragments):
            return tool_name
    return None


def _any_tool(available_tools: list[str]) -> str | None:
    return available_tools[0] if available_tools else None


def _second_tool(available_tools: list[str], exclude: str) -> str:
    """Return a tool different from `exclude`, or fall back to `exclude`."""
    for tool in available_tools:
        if tool != exclude:
            return tool
    return exclude


# ── Main entry point ────────────────────────────────────────────────────────

def call(
    task: str,
    available_tools: list[str],
    tool_results: list[tuple[str, str]],  # [(tool_name, tool_output), …]
) -> LLMOutput:
    """Return a deterministic mock LLM response for the current execution step.

    Args:
        task:            Original user task (used for scenario + tool matching).
        available_tools: Names of tools assigned to this agent.
        tool_results:    Tool calls already completed — [(tool_name, output), …].

    Returns:
        FinalResponse   → runner records an llm_call step and exits the loop.
        ToolCallRequest → runner records a tool_call step and continues.
    """
    task_lower = task.lower()
    scenario = _detect_scenario(task_lower, available_tools)
    n = len(tool_results)  # number of tool steps completed so far

    # ── direct ─────────────────────────────────────────────────────────────
    if scenario == "direct" or not available_tools:
        return FinalResponse(text=_direct_answer(task))

    # ── single_tool ─────────────────────────────────────────────────────────
    if scenario == "single_tool":
        tool = _find_tool_for_task(task_lower, available_tools) or available_tools[0]
        if n == 0:
            return ToolCallRequest(tool_name=tool, tool_input=task)
        tool_name, tool_output = tool_results[0]
        return FinalResponse(text=_single_tool_answer(task, tool_name, tool_output))

    # ── multi_tool ──────────────────────────────────────────────────────────
    if scenario == "multi_tool":
        tool_a = (
            _find_tool_by_type(available_tools, ["search", "web", "lookup"])
            or available_tools[0]
        )
        tool_b = _second_tool(available_tools, tool_a)
        if n == 0:
            return ToolCallRequest(tool_name=tool_a, tool_input=task)
        if n == 1:
            _, out_a = tool_results[0]
            return ToolCallRequest(
                tool_name=tool_b,
                tool_input=f"Process the following and enhance it further: {out_a[:200]}",
            )
        return FinalResponse(text=_multi_tool_answer(task, tool_results))

    # ── tool_failure ────────────────────────────────────────────────────────
    if scenario == "tool_failure":
        tool = _any_tool(available_tools)
        if n == 0:
            # Inject failure sentinel so execute_tool returns an error
            return ToolCallRequest(tool_name=tool, tool_input=f"{_FAIL_SENTINEL}{task}")
        _, tool_output = tool_results[0]
        return FinalResponse(text=_tool_failure_answer(task, tool_results[0][0], tool_output))

    # ── retry ───────────────────────────────────────────────────────────────
    if scenario == "retry":
        tool = _any_tool(available_tools)
        if n == 0:
            # First attempt — inject failure sentinel
            return ToolCallRequest(tool_name=tool, tool_input=f"{_FAIL_SENTINEL}{task}")
        if n == 1:
            _, first_output = tool_results[0]
            if first_output.startswith("ERROR"):
                # Retry — inject retry sentinel so execute_tool succeeds
                return ToolCallRequest(
                    tool_name=tool, tool_input=f"{_RETRY_SENTINEL}{task}"
                )
            # First attempt unexpectedly succeeded
            return FinalResponse(text=_single_tool_answer(task, tool, first_output))
        return FinalResponse(text=_retry_answer(task, tool_results))

    # ── multi_step ──────────────────────────────────────────────────────────
    if scenario == "multi_step":
        tool = _any_tool(available_tools)
        phases = ["PLANNING", "ANALYSIS", "SYNTHESIS"]
        if n < 3:
            phase = phases[n]
            return ToolCallRequest(
                tool_name=tool,
                tool_input=f"{_PHASE_PREFIX}{phase}:{task}",
            )
        return FinalResponse(text=_multi_step_answer(task, tool_results))

    # ── research_pipeline ───────────────────────────────────────────────────
    if scenario == "research_pipeline":
        search_tool = (
            _find_tool_by_type(available_tools, ["search", "web", "lookup"])
            or available_tools[0]
        )
        summary_tool = (
            _find_tool_by_type(available_tools, ["summar"])
            or search_tool
        )
        translate_tool = (
            _find_tool_by_type(available_tools, ["translat"])
            or summary_tool
        )
        pipeline = [
            (search_tool,    task,                                       "Search"),
            (summary_tool,   f"Summarize the key findings about: {task}", "Summarize"),
            (translate_tool, f"Localise and finalise content for: {task}", "Localise"),
        ]
        if n < len(pipeline):
            tool_name, tool_input, _label = pipeline[n]
            return ToolCallRequest(tool_name=tool_name, tool_input=tool_input)
        return FinalResponse(text=_research_pipeline_answer(task, tool_results))

    # Fallback
    return FinalResponse(text=f"Task completed: {task}")


# ── Tool executor ────────────────────────────────────────────────────────────

def execute_tool(tool_name: str, tool_input: str) -> str:
    """Mock tool executor — returns deterministic, richly formatted output.

    Recognises sentinel prefixes injected by call():
      __FAIL__:   → returns a realistic error response
      __RETRY__:  → strips prefix and returns a successful response
      __PHASE__:  → strips prefix, labels output with the reasoning phase
    """
    # ── Sentinel handling ──────────────────────────────────────────────────
    if tool_input.startswith(_FAIL_SENTINEL):
        clean = tool_input[len(_FAIL_SENTINEL):]
        return (
            f"ERROR: The '{tool_name}' service is currently unavailable.\n"
            f"  Reason: Connection timeout after 30 seconds (HTTP 503 Service Unavailable).\n"
            f"  Request: {clean[:120]}\n"
            f"  Trace: upstream dependency failure in data-retrieval layer.\n"
            f"  Suggested action: Retry after 30 seconds or contact support if issue persists."
        )

    is_retry = tool_input.startswith(_RETRY_SENTINEL)
    if is_retry:
        tool_input = tool_input[len(_RETRY_SENTINEL):]

    phase_label = ""
    if tool_input.startswith(_PHASE_PREFIX):
        remainder = tool_input[len(_PHASE_PREFIX):]
        colon_idx = remainder.find(":")
        if colon_idx != -1:
            phase_label = f"[{remainder[:colon_idx]}] "
            tool_input = remainder[colon_idx + 1:]

    retry_prefix = "✓ RETRY SUCCESS — " if is_retry else ""

    # ── Tool-specific responses ────────────────────────────────────────────
    tool_lower = tool_name.lower()

    if any(frag in tool_lower for frag in ["search", "web", "lookup", "query"]):
        return retry_prefix + (
            f"{phase_label}Web search results for '{tool_input}':\n"
            f"  [1] Comprehensive overview published in Q1 2026 — highly relevant to query.\n"
            f"  [2] Peer-reviewed study confirms the primary hypothesis with 94% confidence.\n"
            f"  [3] Industry report highlights 3 actionable recommendations.\n"
            f"  [4] Expert commentary from domain authorities provides nuanced perspective.\n"
            f"  [5] Recent development (March 2026): new findings add important context.\n"
            f"  Total: 5 results retrieved in 0.41s from 3 authoritative sources."
        )

    if any(frag in tool_lower for frag in ["calculat", "math", "comput"]):
        return retry_prefix + (
            f"{phase_label}Calculation for '{tool_input}':\n"
            f"  Primary result:   1,247.83  (standard model)\n"
            f"  Conservative est: 1,089.50  (lower-bound model)\n"
            f"  Optimistic est:   1,412.20  (upper-bound model)\n"
            f"  Formula applied:  base_value × adjustment_factor + margin\n"
            f"  Confidence:       High — all input parameters are well-defined.\n"
            f"  Computed in:      0.003s"
        )

    if any(frag in tool_lower for frag in ["summar"]):
        return retry_prefix + (
            f"{phase_label}Summary of '{tool_input}':\n"
            f"  Core theme:   The subject consists of three interrelated components.\n"
            f"  Key insight:  Component 2 drives ~45% of total variance — highest impact.\n"
            f"  Supporting:   Components 1 and 3 contribute equally to the remainder.\n"
            f"  Complexity:   Medium — non-linear interactions require careful handling.\n"
            f"  Recommendation: Prioritise optimisation of Component 2 for maximum effect.\n"
            f"  Word count reduced from ~1,200 to ~90 (92% compression ratio)."
        )

    if any(frag in tool_lower for frag in ["translat"]):
        return retry_prefix + (
            f"{phase_label}Translation & localisation for '{tool_input}':\n"
            f"  Status:          Complete — target locale confirmed.\n"
            f"  Translated text: [Localised content ready, optimised for target audience]\n"
            f"  Terminology:     8 domain-specific terms adapted to local conventions.\n"
            f"  Cultural notes:  Date formats, units of measure, and 2 idiomatic phrases updated.\n"
            f"  Quality score:   97.4 / 100 — validated against reference corpus.\n"
            f"  Alternate forms: 3 contextual phrasings provided for editorial review."
        )

    if any(frag in tool_lower for frag in ["weather", "forecast"]):
        return retry_prefix + (
            f"{phase_label}Weather data for '{tool_input}':\n"
            f"  Now:      Partly cloudy, 21°C, humidity 58%, wind SW at 14 km/h\n"
            f"  Today:    High 24°C / Low 17°C — 20% chance of afternoon showers\n"
            f"  Tomorrow: Sunny intervals, High 26°C / Low 16°C\n"
            f"  3-day:    Improving conditions; dry weekend expected\n"
            f"  UV index: 4 (moderate) — sun protection recommended between 11:00–15:00\n"
            f"  Source:   National Meteorological Service — updated 5 minutes ago."
        )

    # Generic fallback
    return retry_prefix + (
        f"{phase_label}Tool '{tool_name}' executed for: '{tool_input}'.\n"
        f"  Status:     Success\n"
        f"  Data points: 7 records retrieved\n"
        f"  Confidence:  89%\n"
        f"  Processing:  0.28s\n"
        f"  Output:      Structured result set ready for downstream processing."
    )


# ── Rich answer builders ─────────────────────────────────────────────────────

def _direct_answer(task: str) -> str:
    return (
        f"Here is my answer to: '{task}'\n\n"
        f"This is a well-studied topic with several important dimensions to consider. "
        f"At its core, the subject involves foundational principles that have been validated "
        f"through extensive research and practical application.\n\n"
        f"Key points:\n"
        f"  1. The primary concept is well-defined and widely accepted across the field.\n"
        f"  2. There are three main factors that influence outcomes in this domain.\n"
        f"  3. Recent developments (2025–2026) have refined our understanding significantly.\n\n"
        f"In summary, the answer to your question depends on context, but the general "
        f"consensus points to a clear and actionable conclusion that I've outlined above."
    )


def _single_tool_answer(task: str, tool_name: str, tool_output: str) -> str:
    return (
        f"I've completed the task using the '{tool_name}' tool.\n\n"
        f"Tool output:\n{tool_output}\n\n"
        f"Analysis: The results clearly address your query — '{task}'. "
        f"I've reviewed the output for consistency and accuracy. "
        f"The key takeaway is that the data retrieved is reliable and directly relevant. "
        f"Based on this information, I can confirm the task has been fulfilled successfully."
    )


def _multi_tool_answer(task: str, tool_results: list[tuple[str, str]]) -> str:
    tool_a_name, out_a = tool_results[0]
    tool_b_name, out_b = tool_results[1]
    return (
        f"I completed a two-phase analysis for: '{task}'\n\n"
        f"Phase 1 — {tool_a_name}:\n{out_a}\n\n"
        f"Phase 2 — {tool_b_name}:\n{out_b}\n\n"
        f"Combined insight: The first tool provided raw, comprehensive data while the "
        f"second tool refined, processed, and contextualised the initial findings. "
        f"Cross-referencing both outputs reveals a consistent and detailed picture. "
        f"The synthesis of these two independent sources strengthens the reliability "
        f"of the conclusion and ensures no critical information was missed."
    )


def _tool_failure_answer(task: str, tool_name: str, error_output: str) -> str:
    return (
        f"I attempted to complete '{task}' using the '{tool_name}' tool, "
        f"but encountered a service error:\n\n"
        f"{error_output}\n\n"
        f"Graceful degradation: Despite the tool being unavailable, I can provide "
        f"a partial answer based on my existing knowledge base. "
        f"The topic you've asked about is well-documented, and while live data "
        f"would have enhanced the response, the core answer remains valid:\n\n"
        f"The subject involves established principles that do not change with "
        f"real-time data. I recommend retrying this query once the service recovers. "
        f"If the issue persists, consider an alternative tool or data source."
    )


def _retry_answer(task: str, tool_results: list[tuple[str, str]]) -> str:
    _, first_output = tool_results[0]
    tool_name, retry_output = tool_results[1]
    return (
        f"Task '{task}' completed after one retry.\n\n"
        f"Attempt 1 (failed):\n{first_output}\n\n"
        f"Attempt 2 (succeeded — '{tool_name}'):\n{retry_output}\n\n"
        f"The retry strategy proved effective. The initial failure was a transient "
        f"infrastructure issue that resolved automatically on the second attempt. "
        f"This is expected behaviour for distributed systems under load. "
        f"The final result from the successful retry is accurate and complete."
    )


def _multi_step_answer(task: str, tool_results: list[tuple[str, str]]) -> str:
    phases = ["PLANNING", "ANALYSIS", "SYNTHESIS"]
    phase_outputs = "\n\n".join(
        f"  {phases[i]} phase — '{tool_results[i][0]}':\n  {tool_results[i][1]}"
        for i in range(min(3, len(tool_results)))
    )
    return (
        f"Multi-step structured analysis complete for: '{task}'\n\n"
        f"{phase_outputs}\n\n"
        f"Final synthesis: Each phase built systematically upon the previous one. "
        f"The PLANNING phase identified the problem structure and key variables. "
        f"The ANALYSIS phase examined each variable in depth, revealing non-obvious "
        f"relationships and potential edge cases. "
        f"The SYNTHESIS phase combined all findings into a coherent, evidence-based conclusion. "
        f"This structured approach ensures rigorous coverage and minimises the risk of "
        f"overlooking critical aspects of the problem."
    )


def _research_pipeline_answer(task: str, tool_results: list[tuple[str, str]]) -> str:
    stages = ["Search", "Summarise", "Localise"]
    stage_outputs = "\n\n".join(
        f"  Stage {i + 1} ({stages[i]}) — '{tool_results[i][0]}':\n  {tool_results[i][1]}"
        for i in range(min(3, len(tool_results)))
    )
    return (
        f"Research pipeline completed for: '{task}'\n\n"
        f"{stage_outputs}\n\n"
        f"Executive summary: The full research pipeline has gathered (Stage 1), "
        f"condensed (Stage 2), and localised (Stage 3) all relevant information. "
        f"This multi-stage approach ensures both breadth via web search and depth via "
        f"summarisation, with appropriate localisation for the intended audience. "
        f"The findings are consistent across all pipeline stages and provide a robust, "
        f"ready-to-use knowledge base for informed decision-making."
    )
