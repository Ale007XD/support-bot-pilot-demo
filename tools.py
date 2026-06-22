"""
Tool implementations for support-bot pilot demo.

normalize_intent() is the Authority Projection boundary: a TOTAL function
text -> intent_code in {0,1,2,3}. Every input maps to a code, including the
mandatory default (3=OTHER) for anything unrecognized -- this is what makes
it a legal bridge between LLM content space and the finite, enumerable
authority space the CONDITION steps read (DECISIONS.md, authority-projection
entry, 2026-06-19). An open keyword list without a default would satisfy
"finite output" but not totality -- that gap is the exact failure mode this
function is built to close.

approve_action / deny_action / escalate_action are mock TOOL actions -- no
real ticketing/CRM backend. Each performs the governed action and emits the
notification in one call, then is itself terminal (DECISIONS.md 2026-06-19:
separate TOOL steps per action keep blocked_actions/escalations countable in
ExecutionReceipt; a single TOOL with a mode parameter would hide that signal
inside payload). Fusing action+notify avoids a second next_step hop that the
engine does not honor when a step is reached through nested CONDITION
recursion rather than as a direct inline branch target (see programs.py).
"""
from __future__ import annotations

from typing import Any

from providers import MockAdapter

# Keyword projection: text (case-insensitive substring match) -> intent_code.
# 0=REFUND, 1=DISCOUNT, 2=STATUS, 3=OTHER (mandatory default).
_INTENT_KEYWORDS: dict[str, int] = {
    "REFUND": 0,
    "DISCOUNT": 1,
    "STATUS": 2,
}
_DEFAULT_INTENT_CODE = 3  # OTHER -- catches every unrecognized input

# Shared mutable state for the demo run (no real backend; in a real system
# this would be StateContext.data or an external service call).
_shared: dict[str, Any] = {
    "action_log": [],       # list of (action, reason)
    "notification_log": [], # list of outcome strings
}

_adapter: MockAdapter | None = None


def init_tools(adapter: MockAdapter) -> None:
    global _adapter
    _adapter = adapter
    _shared["action_log"] = []
    _shared["notification_log"] = []


def get_shared() -> dict[str, Any]:
    return _shared


def normalize_intent(**kwargs: Any) -> int:
    """
    Authority Projection: text -> intent_code. TOTAL function -- every input
    maps to a code. First matching keyword wins; no match -> default (OTHER).
    """
    text = str(kwargs.get("text", "")).upper()
    for keyword, code in _INTENT_KEYWORDS.items():
        if keyword in text:
            return code
    return _DEFAULT_INTENT_CODE


def approve_action(**kwargs: Any) -> str:
    reason = kwargs.get("reason", "unknown")
    _shared["action_log"].append(("APPROVED", reason))
    _shared["notification_log"].append("APPROVED")
    return f"approved:{reason}"


def deny_action(**kwargs: Any) -> str:
    reason = kwargs.get("reason", "unknown")
    _shared["action_log"].append(("DENIED", reason))
    _shared["notification_log"].append("DENIED")
    return f"denied:{reason}"


def escalate_action(**kwargs: Any) -> str:
    reason = kwargs.get("reason", "unknown")
    _shared["action_log"].append(("ESCALATED", reason))
    _shared["notification_log"].append("ESCALATED")
    return f"escalated:{reason}"


TOOL_REGISTRY: dict[str, Any] = {
    "normalize_intent": normalize_intent,
    "approve_action": approve_action,
    "deny_action": deny_action,
    "escalate_action": escalate_action,
}
