"""
Unit tests for tools.py — normalize_intent (Authority Projection totality)
and the action tools (approve/deny/escalate).
"""
from __future__ import annotations

import tools
from providers import MockAdapter


def test_normalize_intent_refund() -> None:
    assert tools.normalize_intent(text="I want a REFUND please") == 0


def test_normalize_intent_discount() -> None:
    assert tools.normalize_intent(text="any DISCOUNT available?") == 1


def test_normalize_intent_status() -> None:
    assert tools.normalize_intent(text="order STATUS update") == 2


def test_normalize_intent_other() -> None:
    assert tools.normalize_intent(text="do you sell birthday cakes") == 3


def test_normalize_intent_is_total_on_empty_input() -> None:
    """Authority Projection Principle: f must be total — even '' maps to a code."""
    assert tools.normalize_intent(text="") == 3


def test_normalize_intent_is_total_on_garbage_input() -> None:
    """Unrecognized/garbage text must still map to the default code, not raise."""
    assert tools.normalize_intent(text="asdkjalksdj 12903 !!!@#$") == 3


def test_normalize_intent_case_insensitive() -> None:
    assert tools.normalize_intent(text="refund my order") == 0
    assert tools.normalize_intent(text="Refund My Order") == 0


def test_normalize_intent_missing_text_kwarg_defaults_to_other() -> None:
    """Missing 'text' kwarg must not raise — totality includes malformed calls."""
    assert tools.normalize_intent() == 3


def test_approve_action_logs_and_notifies() -> None:
    tools.init_tools(MockAdapter())
    result = tools.approve_action(reason="STATUS")
    shared = tools.get_shared()
    assert result == "approved:STATUS"
    assert shared["action_log"] == [("APPROVED", "STATUS")]
    assert shared["notification_log"] == ["APPROVED"]


def test_deny_action_logs_and_notifies() -> None:
    tools.init_tools(MockAdapter())
    result = tools.deny_action(reason="DISCOUNT")
    shared = tools.get_shared()
    assert result == "denied:DISCOUNT"
    assert shared["action_log"] == [("DENIED", "DISCOUNT")]
    assert shared["notification_log"] == ["DENIED"]


def test_escalate_action_logs_and_notifies() -> None:
    tools.init_tools(MockAdapter())
    result = tools.escalate_action(reason="REFUND_OR_UNRECOGNIZED")
    shared = tools.get_shared()
    assert result == "escalated:REFUND_OR_UNRECOGNIZED"
    assert shared["action_log"] == [("ESCALATED", "REFUND_OR_UNRECOGNIZED")]
    assert shared["notification_log"] == ["ESCALATED"]


def test_action_and_notification_logs_stay_in_sync() -> None:
    """Action+notify are fused into one call — logs must always be the same length."""
    tools.init_tools(MockAdapter())
    tools.approve_action(reason="STATUS")
    tools.deny_action(reason="DISCOUNT")
    shared = tools.get_shared()
    assert len(shared["action_log"]) == len(shared["notification_log"]) == 2


def test_tool_registry_has_all_four_tools() -> None:
    assert set(tools.TOOL_REGISTRY.keys()) == {
        "normalize_intent",
        "approve_action",
        "deny_action",
        "escalate_action",
    }
