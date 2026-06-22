"""
Mock LLM provider for support-bot pilot demo.

Returns a deterministic classification label for each canned scenario message,
so the demo runs without API keys. Mirrors provider-fallback-demo's
MockAdapter -- no real provider API call.
"""
from __future__ import annotations

from typing import Any

from nano_vm.adapters.base import LLMAdapter

# Canned scenario messages -> classification label the LLM "returns".
# Keys are matched as case-insensitive substrings against the prompt.
_SCENARIOS: dict[str, str] = {
    "i want my money back": "REFUND",
    "can you give me a discount": "DISCOUNT",
    "where is my order": "STATUS",
    "do you sell birthday cakes": "OTHER",
}


class MockAdapter(LLMAdapter):
    """
    Deterministic adapter for the classify_intent step. Looks up the customer
    message embedded in the prompt against a fixed scenario table and returns
    the matching classification label.
    """

    async def complete(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        prompt = messages[-1]["content"] if messages else ""
        lowered = prompt.lower()
        for message_key, label in _SCENARIOS.items():
            if message_key in lowered:
                return label
        # Unrecognized message -> ambiguous classification, exercises the
        # Authority Projection default path (intent_code=3, OTHER).
        return "UNCLEAR"
