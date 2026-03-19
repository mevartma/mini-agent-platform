"""Unit tests for the structured prompt builder."""

import pytest

from app.runner.prompt_builder import build
from tests.conftest import make_agent


def test_prompt_contains_all_three_sections() -> None:
    agent = make_agent()
    prompt = build(agent, "do something")

    assert "SYSTEM INSTRUCTIONS" in prompt
    assert "AVAILABLE TOOLS" in prompt
    assert "USER INPUT" in prompt


def test_sections_appear_in_correct_order() -> None:
    agent = make_agent()
    prompt = build(agent, "test task")

    sys_pos = prompt.index("SYSTEM INSTRUCTIONS")
    tools_pos = prompt.index("AVAILABLE TOOLS")
    input_pos = prompt.index("USER INPUT")

    assert sys_pos < tools_pos < input_pos


def test_system_section_contains_agent_identity() -> None:
    agent = make_agent(name="Research Bot", role="Researcher", description="Finds data.")
    prompt = build(agent, "find something")

    assert "Research Bot" in prompt
    assert "Researcher" in prompt
    assert "Finds data." in prompt


def test_tools_section_lists_all_assigned_tools() -> None:
    agent = make_agent(tool_names=["web-search", "calculator", "summarizer"])
    prompt = build(agent, "do a task")

    assert "web-search" in prompt
    assert "calculator" in prompt
    assert "summarizer" in prompt


def test_tools_section_notes_no_tools_when_empty() -> None:
    agent = make_agent(tool_names=[])
    prompt = build(agent, "do a task")

    assert "no tools assigned" in prompt


def test_user_input_section_contains_exact_task() -> None:
    task = "Summarise the annual report for FY2025."
    agent = make_agent()
    prompt = build(agent, task)

    assert task in prompt


def test_user_input_is_in_last_section() -> None:
    task = "unique-task-string-xyz"
    agent = make_agent()
    prompt = build(agent, task)

    # Task should appear after the USER INPUT header
    input_header_pos = prompt.index("USER INPUT")
    task_pos = prompt.index(task)
    assert task_pos > input_header_pos
