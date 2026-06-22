# support-bot-pilot-demo

FSM-governed customer support triage pilot, built on [llm-nano-vm](https://pypi.org/project/llm-nano-vm/).

The LLM classifies the customer message. The FSM decides what happens next — the model's raw text never reaches the action layer directly.

```
classify_intent [LLM]
    -> normalize_intent [TOOL]   text -> intent_code (0..3), total function
    -> policy_gate_1 [CONDITION] intent_code == 0 (REFUND)   -> escalate_action
    -> policy_gate_2 [CONDITION] intent_code == 1 (DISCOUNT) -> deny_action
    -> policy_gate_3 [CONDITION] intent_code == 2 (STATUS)   -> approve_action
                                  otherwise (OTHER=3)        -> escalate_action
```

Each action step (`approve_action` / `deny_action` / `escalate_action`) performs the governed action and emits the notification in a single TOOL call, then is itself terminal. `ExecutionReceipt` shows which action actually ran — not what the LLM said it would do.

## Run

```bash
pip install ".[dev]"
python support_demo.py --scenario refund
python support_demo.py --all
```

## Test

```bash
pytest tests/ -v
mypy --strict programs.py tools.py providers.py support_demo.py tests/
ruff check .
```

## Status

Pilot/demo — mock TOOL actions, no real ticketing/CRM backend. Part of the `support_bot_pilot` chain in the nano-vm ecosystem (see `sprint_support_program`).

## License

MIT
