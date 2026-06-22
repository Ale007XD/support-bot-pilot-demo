"""
End-to-end tests: real ExecutionVM.run() through the full FSM for all four
support-triage scenarios. Regression-guards the CONDITION->CONDITION next_step
gap documented in DECISIONS.md (2026-06-20) -- action and notification must
always agree, since they are fused into one TOOL call per action step.
"""
from __future__ import annotations

import pytest
from nano_vm.analyzer import TraceAnalyzer
from nano_vm.validator import ProgramValidator
from nano_vm.vm import ExecutionVM

from programs import build_program
from providers import MockAdapter
from tools import TOOL_REGISTRY, get_shared, init_tools

_SCENARIOS = {
    "refund": ("I want my money back, this is unacceptable.", "ESCALATED"),
    "discount": ("Can you give me a discount on my next order?", "DENIED"),
    "status": ("Where is my order? It's been a week.", "APPROVED"),
    "other": ("Do you sell birthday cakes?", "ESCALATED"),
}


@pytest.fixture(autouse=True)
def _validate_program_first() -> None:
    """Every E2E test runs only after the program passes the validator gate."""
    report = ProgramValidator(build_program()).validate()
    assert report.is_valid()


@pytest.mark.parametrize("scenario", list(_SCENARIOS.keys()))
@pytest.mark.asyncio
async def test_scenario_produces_expected_action(scenario: str) -> None:
    message, expected_action = _SCENARIOS[scenario]

    adapter = MockAdapter()
    init_tools(adapter)
    program = build_program()
    vm = ExecutionVM(llm=adapter, tools=TOOL_REGISTRY)

    trace = await vm.run(program, context={"customer_message": message})

    shared = get_shared()
    assert shared["action_log"], f"no action recorded for scenario={scenario}"
    action, _reason = shared["action_log"][0]
    assert action == expected_action

    analyzer = TraceAnalyzer(trace)
    receipt = analyzer.receipt()
    assert str(receipt.final_status).split(".")[-1] == "SUCCESS"


@pytest.mark.parametrize("scenario", list(_SCENARIOS.keys()))
@pytest.mark.asyncio
async def test_action_and_notification_always_match(scenario: str) -> None:
    """
    Regression guard for DECISIONS.md 2026-06-20 finding: action and notify
    must always be the same outcome, since they are fused into a single
    TOOL call per action step (no second next_step hop to drift out of sync).
    """
    message, _expected = _SCENARIOS[scenario]

    adapter = MockAdapter()
    init_tools(adapter)
    program = build_program()
    vm = ExecutionVM(llm=adapter, tools=TOOL_REGISTRY)

    await vm.run(program, context={"customer_message": message})

    shared = get_shared()
    action, _reason = shared["action_log"][0]
    notification = shared["notification_log"][0]
    assert action == notification, (
        f"action/notify mismatch for scenario={scenario}: "
        f"action={action} notification={notification}"
    )


@pytest.mark.asyncio
async def test_unrecognized_message_falls_through_to_escalate() -> None:
    """
    Authority Projection default path: an unmapped/ambiguous message must
    still resolve to intent_code=3 (OTHER) -> escalate_action, never raise
    and never silently fall through with no action taken.
    """
    adapter = MockAdapter()
    init_tools(adapter)
    program = build_program()
    vm = ExecutionVM(llm=adapter, tools=TOOL_REGISTRY)

    await vm.run(program, context={"customer_message": "completely unrelated gibberish"})

    shared = get_shared()
    assert shared["action_log"], "default path must still take an action"
    action, _reason = shared["action_log"][0]
    assert action == "ESCALATED"
