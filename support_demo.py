"""
nano-vm support-bot triage demo.

Usage:
    python support_demo.py --scenario refund
    python support_demo.py --scenario discount
    python support_demo.py --scenario status
    python support_demo.py --scenario other
    python support_demo.py --all          # runs all scenarios + comparison table
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from nano_vm.analyzer import TraceAnalyzer
from nano_vm.validator import ProgramValidator
from nano_vm.vm import ExecutionVM

from programs import build_program
from providers import MockAdapter
from tools import TOOL_REGISTRY, get_shared, init_tools

_SCENARIO_MESSAGES: dict[str, str] = {
    "refund": "I want my money back, this is unacceptable.",
    "discount": "Can you give me a discount on my next order?",
    "status": "Where is my order? It's been a week.",
    "other": "Do you sell birthday cakes?",
}


def validate_program() -> None:
    """Gate: ProgramValidator.is_valid() must be True before any run."""
    program = build_program()
    report = ProgramValidator(program).validate()
    if not report.is_valid():
        print("PROGRAM VALIDATION FAILED:")
        print(report.summary())
        raise SystemExit(1)


def run_scenario(scenario: str) -> dict[str, object]:
    """Run one scenario, return summary dict."""
    message = _SCENARIO_MESSAGES[scenario]

    adapter = MockAdapter()
    init_tools(adapter)

    program = build_program()
    vm = ExecutionVM(llm=adapter, tools=TOOL_REGISTRY)
    trace = asyncio.run(vm.run(program, context={"customer_message": message}))

    analyzer = TraceAnalyzer(trace)
    receipt = analyzer.receipt()

    shared = get_shared()
    action_log: list[tuple[str, str]] = shared.get("action_log", [])
    notification_log: list[str] = shared.get("notification_log", [])

    return {
        "scenario": scenario,
        "message": message,
        "trace_id": receipt.trace_id,
        "trace_hash": receipt.trace_hash,
        "final_status": str(receipt.final_status).split(".")[-1],
        "completed_steps": len([s for s in trace.steps if str(s.status).endswith("SUCCESS")]),
        "failed_steps": receipt.failed_steps,
        "rejected_transitions": len(receipt.rejected_transitions),
        "action": action_log[0][0] if action_log else "NONE",
        "action_reason": action_log[0][1] if action_log else "NONE",
        "notification": notification_log[0] if notification_log else "NONE",
        "rejected_details": [dataclasses.asdict(rt) for rt in receipt.rejected_transitions],
    }


def print_scenario(result: dict[str, object]) -> None:
    scenario = result["scenario"]
    print(f"\n{'='*60}")
    print(f"=== Scenario: {str(scenario).upper()} ===")
    print(f"{'='*60}")
    print(f"\nCustomer: \"{result['message']}\"")
    print(f"\nclassify_intent -> normalize_intent -> policy_gate(s) -> {result['action']}")
    print(f"  action: {result['action']}  (reason={result['action_reason']})")
    print(f"  notify: {result['notification']}")

    print("\nRECEIPT:")
    receipt_display = {
        "final_status": result["final_status"],
        "action": result["action"],
        "completed_steps": result["completed_steps"],
        "failed_steps": result["failed_steps"],
        "rejected_transitions": result["rejected_transitions"],
        "trace_hash": result["trace_hash"],
    }
    print(json.dumps(receipt_display, indent=2))


def print_comparison(results: list[dict[str, object]]) -> None:
    print(f"\n{'='*60}")
    print("=== COMPARISON TABLE ===")
    print(f"{'='*60}")
    headers = ["Scenario", "Action", "Final Status", "Trace Hash"]
    col = [14, 14, 16, 16]
    print("  " + "".join(h.ljust(c) for h, c in zip(headers, col)))
    print("  " + "-" * sum(col))
    for r in results:
        row = [
            str(r["scenario"]),
            str(r["action"]),
            str(r["final_status"]),
            str(r["trace_hash"])[:12] + "...",
        ]
        print("  " + "".join(v.ljust(c) for v, c in zip(row, col)))

    print(f"\n  {'-'*58}")
    print("  Four different customer messages. Four different FSM paths.")
    print("  The LLM classifies. The FSM decides what happens next.")
    print(f"  {'-'*58}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="nano-vm support-bot triage demo")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scenario", choices=list(_SCENARIO_MESSAGES.keys()))
    group.add_argument("--all", action="store_true")
    args = parser.parse_args()

    validate_program()

    if args.all:
        results = [run_scenario(s) for s in _SCENARIO_MESSAGES]
        for r in results:
            print_scenario(r)
        print_comparison(results)
    else:
        r = run_scenario(args.scenario)
        print_scenario(r)


if __name__ == "__main__":
    main()
