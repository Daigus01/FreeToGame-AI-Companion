"""P2-03: cards only for games named in the assistant text. Also P2-05 history trimming."""
import asyncio

from app.llm.cards import select_cards
from app.llm.history import trim_history
from app.llm.orchestrator import run_chat
from app.llm.providers import ProviderEvent, ToolCall
from tests.test_tools import FakeClient


def pool(*titles):
    return {i: {"id": i, "title": t} for i, t in enumerate(titles, start=1)}


def ids(cards): return [c["id"] for c in cards]


def test_whole_word_case_insensitive_and_order_of_mention():
    p = pool("G1", "G10", "Apex Legends")
    assert ids(select_cards("Prueba APEX legends y luego G1.", p)) == [3, 1]
    assert ids(select_cards("Te sugiero G10", p)) == [2]  # G1 is not inside G10


def test_longer_title_swallows_shorter_one():
    p = pool("Dota", "Dota 2")
    assert ids(select_cards("Juega Dota 2, es genial", p)) == [2]
    assert ids(select_cards("Juega Dota y Dota 2", p)) == [1, 2] or ids(select_cards("Juega Dota y Dota 2", p)) == [2, 1]


def test_special_chars_none_and_cap():
    p = pool("Lost Ark: Next (Beta)", "Z" * 3)
    assert ids(select_cards("Mira Lost Ark: Next (Beta).", p)) == [1]
    assert select_cards("nada relevante", p) == [] and select_cards("", p) == []
    many = pool(*[f"Game{c}" for c in "abcdefghij"])
    assert len(select_cards(" ".join(g["title"] for g in many.values()), many)) == 6


class Script:
    def __init__(self, calls, final): self.calls, self.final, self.n = calls, final, 0

    async def stream(self, messages):
        self.n += 1
        if self.n == 1 and self.calls:
            for i, (name, args) in enumerate(self.calls):
                yield ProviderEvent("tool_call", tool_call=ToolCall(f"c{i}", name, args))
        else:
            yield ProviderEvent("text", text=self.final)


def run(provider):
    async def go(): return [e async for e in run_chat(provider, FakeClient(), [], "q")]
    return asyncio.run(go())


def test_no_mention_means_no_cards_event():
    ev = run(Script([("get_games_by_filter", {})], "¿Qué género te gusta más?"))
    assert [e["type"] for e in ev] == ["tool_call", "token", "done"]


def test_single_detail_fallback_shows_that_game():
    ev = run(Script([("get_game_details", {"game_id": 4})], "Es un gran juego, te lo recomiendo."))
    assert [g["id"] for g in next(e for e in ev if e["type"] == "games")["games"]] == [4]


def test_text_before_and_after_tools_counts():
    ev = run(Script([("get_games_by_filter", {})], "Te recomiendo G2 y G3 (G99 no existe)."))
    assert [g["id"] for g in next(e for e in ev if e["type"] == "games")["games"]] == [2, 3]  # G99 never came from a tool


# ---------- history trimming ----------
def u(t): return {"role": "user", "content": t}
def a(t, tc=False): return {"role": "assistant", "content": t, "tool_calls": [{"id": "1", "type": "function", "function": {"name": "n", "arguments": "{}"}}] if tc else None}
def tool(t): return {"role": "tool", "tool_call_id": "1", "content": t}


def test_trim_noop_when_small():
    h = [u("hola"), a("hi")]
    assert trim_history(h, 1000) == h


def test_trim_drops_oldest_and_starts_at_user():
    h = [u("x" * 50), a("", tc=True), tool("y" * 500), a("r" * 50), u("q"), a("ok")]
    out = trim_history(h, 100)  # must drop first turn; window may not start at the orphan assistant/tool
    assert out[0]["role"] == "user" and out == [u("q"), a("ok")]


def test_trim_everything_when_nothing_fits_and_empty():
    assert trim_history([u("x" * 500)], 10) == [] and trim_history([], 10) == []
