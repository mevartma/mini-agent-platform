"""Prompt injection guardrail.

Uses deterministic regex heuristics to detect common prompt injection patterns.
This is a best-effort defence — it demonstrates awareness of the attack class
without claiming production-grade coverage. Obfuscated or multi-language
attacks are out of scope.
"""

import re

# Each pattern targets a distinct injection technique.
# All patterns are compiled once at import time.
_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        # Classic override attempts — allow any number of modifier words before "instructions"
        r"ignore\s+(\w+\s+){0,4}instructions?",
        r"disregard\s+(\w+\s+){0,4}instructions?",
        r"forget\s+(everything|all|your\s+instructions?|what\s+you\s+were\s+told)",
        # Role / persona hijacking
        r"\byou\s+are\s+now\b",
        r"\bact\s+as\b",
        r"\bpretend\s+(you\s+are|to\s+be)\b",
        r"\byour\s+new\s+(role|persona|instructions?)\b",
        r"\bswitch\s+(your\s+)?(role|mode|persona)\b",
        # System prompt extraction
        r"\breveal\s+(your\s+|the\s+)?(system\s+)?(prompt|instructions?|context)\b",
        r"\bprint\s+(your\s+)?(system\s+)?prompt\b",
        r"\bshow\s+(me\s+)?(your\s+)?(system\s+)?prompt\b",
        r"\btell\s+me\s+(your\s+)?(system\s+)?(prompt|instructions?|context)\b",
        r"\brepeat\s+(your\s+)?(system\s+)?instructions?\b",
        # Jailbreak / bypass keywords
        r"\bjailbreak\b",
        r"\bDAN\b",
        r"\bdo\s+anything\s+now\b",
        r"\bbypass\s+(your\s+)?(safety|filter|guardrail|restriction)",
        r"\boverride\s+(your\s+)?(safety|filter|guardrail|restriction|instructions?)",
        r"\bdeveloper\s+mode\b",
        r"\bgrandma\s+trick\b",
        # Delimiter injection (trying to inject new system turns)
        r"<\s*system\s*>",
        r"\[INST\]",
        r"###\s*(system|instruction)",
    ]
]


class PromptInjectionError(Exception):
    """Raised when a prompt injection attempt is detected."""


def check(task: str) -> None:
    """Raise PromptInjectionError if the task contains injection patterns.

    Args:
        task: The raw user-supplied task string.

    Raises:
        PromptInjectionError: If an injection pattern is matched.
    """
    for pattern in _PATTERNS:
        if pattern.search(task):
            raise PromptInjectionError(
                "Prompt injection detected. Request rejected."
            )
