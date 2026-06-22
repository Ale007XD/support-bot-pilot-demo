"""
FSM program: customer support triage with policy-gated actions.

Flow:
  classify_intent [LLM]
      → normalize_intent [TOOL]  text -> intent_code (0..3), TOTAL function
      → policy_gate_1 [CONDITION] intent_code == 0 (REFUND)
            then      -> escalate_action [terminal]
            otherwise -> policy_gate_2
      → policy_gate_2 [CONDITION] intent_code == 1 (DISCOUNT)
            then      -> deny_action [terminal]
            otherwise -> policy_gate_3
      → policy_gate_3 [CONDITION] intent_code == 2 (STATUS)
            then      -> approve_action [terminal]
            otherwise -> escalate_action [terminal] (OTHER=3 + default fallback)

Each action step (approve_action/deny_action/escalate_action) performs the
governed action AND emits the notification in a single TOOL call, then is
itself terminal. This sidesteps an engine constraint discovered while
building this program: ExecutionVM._execute_loop only consults a step's
next_step field when that step is reached as a *direct* inline branch target
of the *immediately enclosing* CONDITION. When a CONDITION's branch target is
itself a CONDITION (policy_gate_1 -> policy_gate_2), the engine recurses via
a fresh _execute_loop call seeded with the inner CONDITION's own branch
result as start_step_id -- so the action step named there is entered as a
plain sequential step, not as an inline branch target, and any next_step set
on it is silently ignored (array order wins instead). Action+notify fused
into one terminal step removes the need for that second hop entirely.

Authority Projection Principle (DECISIONS.md 2026-06-19):
  normalize_intent is a TOTAL function text -> {0,1,2,3}. Every input maps to
  a code, including a mandatory default (3=OTHER) for anything unrecognized.
  The LLM never reaches policy_gate directly -- its raw text is reduced to a
  numeric sentinel BEFORE the decision boundary. ASTEngine does not support
  string-literal RHS in comparisons (CONSTRAINTS.md), so every gate compares
  $intent_code against an integer, never a quoted string.

Decision boundary placement (DECISIONS.md, creative-control-session 2026-06-19):
  classify_intent's raw text is never read downstream -- only normalize_intent's
  numeric projection is. The LLM call here is a CLASSIFY step (its output feeds
  a CONDITION), not a CREATIVE step, even though the call looks "creative" on
  the surface.

This is a pilot/demo program with MockAdapter and mock TOOL actions -- no real
ticketing backend. Mirrors the construction of provider-fallback-demo
(github.com/Ale007XD/provider-fallback-demo): provider-agnostic DSL, real
llm-nano-vm stack, deterministic responses so the demo runs without API keys.
"""
from __future__ import annotations

from nano_vm.models import Program, Step, StepType


def build_program() -> Program:
    """Build the support-bot triage program."""
    return Program(
        name="support_bot_triage",
        description="Customer support: LLM classifies intent, FSM owns the action.",
        steps=[
            # --- Step 1: classify intent (CLASSIFY-position LLM call) ---
            Step(
                id="classify_intent",
                type=StepType.LLM,
                prompt=(
                    "Classify the customer message into exactly one category: "
                    "REFUND, DISCOUNT, STATUS, or OTHER. "
                    "Message: $customer_message"
                ),
                output_key="raw_intent",
                next_step="normalize_intent",
            ),
            # --- Step 2: Authority Projection -- total function text -> code ---
            Step(
                id="normalize_intent",
                type=StepType.TOOL,
                tool="normalize_intent",
                args={"text": "$raw_intent"},
                output_key="intent_code",
                next_step="policy_gate_1",
            ),
            # --- Step 3: policy gates (numeric sentinel only, no string RHS) ---
            Step(
                id="policy_gate_1",
                type=StepType.CONDITION,
                condition="$intent_code == 0",  # REFUND
                then="escalate_action",
                otherwise="policy_gate_2",
            ),
            Step(
                id="policy_gate_2",
                type=StepType.CONDITION,
                condition="$intent_code == 1",  # DISCOUNT
                then="deny_action",
                otherwise="policy_gate_3",
            ),
            Step(
                id="policy_gate_3",
                type=StepType.CONDITION,
                condition="$intent_code == 2",  # STATUS
                then="approve_action",
                otherwise="escalate_action",  # OTHER=3 + default fallback
            ),
            # --- Step 4: action (TOOL+CONDITION separated per BFS constraint).
            # Each action tool performs the governed action AND emits the
            # notification in one call -- avoids relying on next_step being
            # honored on a step reached via nested CONDITION recursion (the
            # engine only consults next_step for a step reached as a direct
            # inline branch target of the *immediately enclosing* CONDITION;
            # a target reached through a recursive sub-branch is entered as
            # a fresh sequential step and next_step is silently ignored).
            # Each action step is itself terminal -- no further hop needed.
            Step(
                id="approve_action",
                type=StepType.TOOL,
                tool="approve_action",
                args={"reason": "STATUS"},
                output_key="action_result",
                is_terminal=True,
            ),
            Step(
                id="deny_action",
                type=StepType.TOOL,
                tool="deny_action",
                args={"reason": "DISCOUNT"},
                output_key="action_result",
                is_terminal=True,
            ),
            Step(
                id="escalate_action",
                type=StepType.TOOL,
                tool="escalate_action",
                args={"reason": "REFUND_OR_UNRECOGNIZED"},
                output_key="action_result",
                is_terminal=True,
            ),
        ],
    )
