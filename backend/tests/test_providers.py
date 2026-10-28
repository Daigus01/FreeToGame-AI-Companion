"""AnthropicProvider (translation + streaming with a fake SDK client) and MockProvider. P2-07, D-14."""
import asyncio
import json
from types import SimpleNamespace

from app.llm.mock import MockProvider, parse_query
from app.llm.orchestrator import run_chat
from app.llm.providers import AnthropicProvider, get_provider, to_anthropic_messages
from app.config import Settings
from tests.test_tools import FakeClient

TC = {"id": "t1", "type": "function", "function": {"name": "get_games_by_filter", "arguments": json.dumps({"category": "mmorpg"})}}


def test_translation_roles_blocks_and_merging():
    msgs = [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "voy a buscar", "tool_calls": [TC, {**TC, "id": "t2"}]},
        {"role": "tool", "tool_call_id": "t1", "content": "{\"a\":1}"},
        {"role": "tool", "tool_call_id": "t2", "content": "{\"b\":2}"},
    ]
    system, out = to_anthropic_messages(msgs)
    assert system == "SYS" and [m["role"] for m in out] == ["user", "assistant", "user"]
    assert [b["type"] for b in out[1]["content"]] == ["text", "tool_use", "tool_use"]
    assert out[1]["content"][1]["input"] == {"category": "mmorpg"}
    # both tool results merged into ONE user message, in order
    assert [(b["type"], b["tool_use_id"]) for b in out[2]["content"]] == [("tool_result", "t1"), ("tool_result", "t2")]


def test_translation_assistant_without_text_and_bad_json_args():
    bad = {**TC, "function": {"name": "x", "arguments": "{oops"}}
    _, out = to_anthropic_messages([{"role": "user", "content": "q"}, {"role": "assistant", "content": None, "tool_calls": [bad]}])
    assert out[1]["content"] == [{"type": "tool_use", "id": "t1", "name": "x", "input": {}}]


class FakeStream:
    def __init__(self, texts, blocks): self._t, self._b = texts, blocks

    async def __aenter__(self):
        async def gen():
            for t in self._t: yield t
        self.text_stream = gen(); return self

    async def __aexit__(self, *a): return False
    async def get_final_message(self): return SimpleNamespace(content=self._b)


class FakeAnthropic:
    def __init__(self, texts, blocks):
        self.seen = {}
        outer = self

        class M:
            def stream(self, **kw):
                outer.seen = kw
                return FakeStream(texts, blocks)

        self.messages = M()


def collect(provider, messages):
    async def go(): return [e async for e in provider.stream(messages)]
    return asyncio.run(go())


def test_anthropic_stream_text_and_tool_use():
    blocks = [SimpleNamespace(type="text", text="x"), SimpleNamespace(type="tool_use", id="tu1", name="get_game_details", input={"game_id": 3})]
    fake = FakeAnthropic(["Hola ", "mundo"], blocks)
    ev = collect(AnthropicProvider("k", "m", client=fake), [{"role": "system", "content": "S"}, {"role": "user", "content": "q"}])
    assert [(e.type, e.text) for e in ev[:2]] == [("text", "Hola "), ("text", "mundo")]
    assert ev[2].tool_call.name == "get_game_details" and ev[2].tool_call.arguments == {"game_id": 3} and len(ev) == 3
    assert fake.seen["system"] == "S" and fake.seen["model"] == "m" and fake.seen["tools"][0]["input_schema"]


def test_get_provider_selects_mock_and_anthropic_needs_no_network():
    assert isinstance(get_provider(Settings(llm_provider="mock")), MockProvider)
    assert isinstance(get_provider(Settings(llm_provider="anthropic", anthropic_api_key="sk-test")), AnthropicProvider)


def test_parse_query():
    assert parse_query("Busco un MMORPG de fantasía para PC que no sea muy antiguo") == {"category": "mmorpg", "platform": "pc", "sort_by": "release-date"}
    assert parse_query("juegos de disparos en el navegador, populares") == {"category": "shooter", "platform": "browser", "sort_by": "popularity"}
    assert parse_query("hola") == {}


def test_mock_full_turn_through_orchestrator():
    async def go(): return [e async for e in run_chat(MockProvider(), FakeClient(), [], "dame un mmorpg para pc")]
    ev = asyncio.run(go())
    types = [e["type"] for e in ev]
    assert types[0] == "tool_call" and types[-1] == "done" and "games" in types
    cards = next(e for e in ev if e["type"] == "games")["games"]
    assert [g["title"] for g in cards] == ["G1", "G2", "G3"]  # mock names the first 3 results -> cards for exactly those
