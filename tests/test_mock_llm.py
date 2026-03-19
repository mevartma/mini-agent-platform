"""Unit tests for the mock LLM adapter."""

import pytest

from app.runner.mock_llm import FinalResponse, ToolCallRequest, call, execute_tool


# ── call() behaviour ──────────────────────────────────────────────────────────

def test_no_tools_returns_final_response() -> None:
    result = call("tell me a joke", [], [])
    assert isinstance(result, FinalResponse)


def test_no_matching_tool_returns_final_response() -> None:
    result = call("tell me a joke", ["calculator"], [])
    assert isinstance(result, FinalResponse)


def test_action_keyword_with_matching_tool_returns_tool_call() -> None:
    result = call("search for recent AI news", ["web-search"], [])
    assert isinstance(result, ToolCallRequest)
    assert result.tool_name == "web-search"


def test_tool_call_includes_original_task_as_input() -> None:
    task = "find the latest stock prices"
    result = call(task, ["web-search"], [])
    assert isinstance(result, ToolCallRequest)
    assert result.tool_input == task


def test_existing_tool_results_produce_final_response() -> None:
    result = call(
        "search for news",
        ["web-search"],
        [("web-search", "result 1, result 2")],
    )
    assert isinstance(result, FinalResponse)


def test_final_response_references_tool_output() -> None:
    tool_output = "some important data"
    result = call("find data", ["web-search"], [("web-search", tool_output)])
    assert isinstance(result, FinalResponse)
    assert tool_output in result.text


def test_determinism_same_input_same_output() -> None:
    kwargs = dict(
        task="search for news",
        available_tools=["web-search"],
        tool_results=[],
    )
    assert call(**kwargs) == call(**kwargs)


@pytest.mark.parametrize(
    "task,tool,expected_type",
    [
        ("search for dogs", ["web-search"], ToolCallRequest),
        ("find a recipe", ["web-search"], ToolCallRequest),
        ("look up the docs", ["lookup-tool"], ToolCallRequest),
        ("calculate 2+2", ["calculator"], ToolCallRequest),
        ("compute the average", ["math-tool"], ToolCallRequest),
        ("summarize this article", ["summarizer"], ToolCallRequest),
        ("translate to French", ["translator"], ToolCallRequest),
        ("what is the weather", ["weather-api"], ToolCallRequest),
        ("just say hello", ["web-search"], FinalResponse),  # no matching keyword
    ],
)
def test_keyword_to_tool_matching(
    task: str, tool: list[str], expected_type: type
) -> None:
    result = call(task, tool, [])
    assert isinstance(result, expected_type)


# ── execute_tool() behaviour ──────────────────────────────────────────────────

def test_known_tool_returns_specific_response() -> None:
    result = execute_tool("web-search", "python tutorials")
    assert "python tutorials" in result


def test_unknown_tool_returns_generic_response() -> None:
    result = execute_tool("my-custom-tool", "some input")
    assert "my-custom-tool" in result
    assert "some input" in result


def test_tool_name_fragment_matching() -> None:
    # "my-web-search-v2" contains "web-search" → should match
    result = execute_tool("my-web-search-v2", "query")
    assert "query" in result
    assert "mock output" not in result.lower() or "Search results" in result
