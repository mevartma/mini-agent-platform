"""Namespaced Redis key helpers."""


def agent_key(tenant_id: str, agent_id: str) -> str:
    return f"tenant:{tenant_id}:agent:{agent_id}"


def tool_key(tenant_id: str, tool_id: str) -> str:
    return f"tenant:{tenant_id}:tool:{tool_id}"
