"""
Tests for programs.py — ProgramValidator gate and DSL structure.
"""
from __future__ import annotations

from nano_vm.models import StepType
from nano_vm.validator import IssueKind, IssueSeverity, ProgramValidator

from programs import build_program


def test_program_is_valid() -> None:
    """Gate: ProgramValidator.is_valid() must be True (PV-13 requirement)."""
    report = ProgramValidator(build_program()).validate()
    assert report.is_valid() is True


def test_program_has_no_error_severity_issues() -> None:
    report = ProgramValidator(build_program()).validate()
    errors = [i for i in report.issues if i.severity == IssueSeverity.ERROR]
    assert errors == []


def test_program_no_failure_terminal_warning_is_expected() -> None:
    """
    This pilot has no execution-failure terminal (mock actions never fail) --
    PV-13 emits NO_FAILURE_TERMINAL as WARNING, which does not block is_valid().
    This test documents that the warning is expected, not a regression.
    """
    report = ProgramValidator(build_program()).validate()
    warnings = [i for i in report.issues if i.severity == IssueSeverity.WARNING]
    kinds = {w.kind for w in warnings}
    assert IssueKind.NO_FAILURE_TERMINAL in kinds or warnings == []


def test_terminal_steps_are_at_end_of_steps_list() -> None:
    """DSL invariant: is_terminal=True steps must be placed at end of steps[]."""
    program = build_program()
    terminal_flags = [s.is_terminal for s in program.steps]
    # once a terminal step starts, no non-terminal step should follow
    first_terminal_idx = next(
        (i for i, t in enumerate(terminal_flags) if t), len(terminal_flags)
    )
    assert all(terminal_flags[first_terminal_idx:])


def test_action_steps_are_terminal() -> None:
    """approve/deny/escalate are each terminal — no second next_step hop."""
    program = build_program()
    by_id = {s.id: s for s in program.steps}
    for action_id in ("approve_action", "deny_action", "escalate_action"):
        assert by_id[action_id].is_terminal is True
        assert by_id[action_id].next_step is None


def test_policy_gates_use_numeric_sentinel_not_string_literal() -> None:
    """
    ASTEngine constraint: no string-literal RHS in comparisons. Every gate
    condition must compare against an integer, never a quoted string.
    """
    program = build_program()
    gates = [s for s in program.steps if s.type == StepType.CONDITION]
    assert len(gates) == 3
    for gate in gates:
        assert gate.condition is not None
        assert '"' not in gate.condition
        assert "'" not in gate.condition


def test_classify_intent_feeds_normalize_intent_not_policy_gate_directly() -> None:
    """
    Decision boundary placement: classify_intent's raw output must be
    projected through normalize_intent before any CONDITION reads it.
    """
    program = build_program()
    by_id = {s.id: s for s in program.steps}
    assert by_id["classify_intent"].next_step == "normalize_intent"
    assert by_id["normalize_intent"].next_step == "policy_gate_1"


def test_program_has_exactly_three_action_terminals() -> None:
    program = build_program()
    terminals = [s.id for s in program.steps if s.is_terminal]
    assert set(terminals) == {"approve_action", "deny_action", "escalate_action"}
