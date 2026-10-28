"""Orchestrator loop test with a scripted fake LLM provider (no network)."""
import asyncio

from app.llm.orchestrator import run_chat
from app.llm.providers import ProviderEvent, ToolCall
from tests.test_tools import FakeClient


class ScriptedProvider:
    """Round 1: asks for a tool. Round 2: answers with text."""

    def __init__(self):
        self.round = 0

    async def stream(self, messages):
        self.round += 1
        if self.round == 1:
            yield ProviderEvent("tool_call", tool_call=ToolCall("c1", "get_games_by_filter", {"category": "mmorpg"}))
        else:
            assert messages[-1]["role"] == "tool"  # tool result was fed back
            yield ProviderEvent("text", text="Te recomiendo ")
            yield ProviderEvent("text", text="G1.")


def collect():
    async def go():
        return [e async for e in run_chat(ScriptedProvider(), FakeClient(), [], "busco mmorpg")]

    return asyncio.run(go())


def test_tool_roundtrip_streams_tokens_cards_and_done():
    events = collect()
    types = [e["type"] for e in events]
    assert types == ["tool_call", "token", "token", "games", "done"]
    assert [g["id"] for g in events[3]["games"]] == [1]  # only the game named in the text ("G1", not "G10") gets a card (P2-03)
    roles = [m["role"] for m in events[-1]["new_messages"]]
    assert roles == ["user", "assistant", "tool", "assistant"]


class FailingProvider:
    async def stream(self, messages):
        raise RuntimeError("boom")
        yield  # pragma: no cover


def test_provider_failure_yields_error_event():
    async def go():
        return [e async for e in run_chat(FailingProvider(), FakeClient(), [], "hola")]

    assert asyncio.run(go())[0]["type"] == "error"
