"""Deterministic, key-less LLM stand-in for development and tests (LLM_PROVIDER=mock, D-14).
STATUS: done + tested. NOT a language model: it maps keywords to ONE get_games_by_filter call, then names up to 3
returned games. It exists so the whole chat path (SSE, tools, cards, persistence, UI) can be exercised for free.
Follow-up questions are NOT understood (it just searches again)."""
import json
import re
from collections.abc import AsyncIterator

from app.llm.providers import ProviderEvent, ToolCall

CATEGORY_WORDS = {
    "mmorpg": "mmorpg", "shooter": "shooter", "disparo": "shooter", "pvp": "pvp", "moba": "moba", "anime": "anime",
    "estrategia": "strategy", "strategy": "strategy", "fantas": "fantasy", "fantasy": "fantasy", "ciencia ficci": "sci-fi",
    "sci-fi": "sci-fi", "carta": "card", "card": "card", "carrera": "racing", "racing": "racing", "pelea": "fighting",
    "fighting": "fighting", "social": "social", "deporte": "sports", "sports": "sports", "survival": "survival",
    "supervivencia": "survival", "terror": "horror", "horror": "horror", "zombi": "zombie", "zombie": "zombie",
}


def parse_query(text: str) -> dict:
    t = text.lower()
    args: dict = {}
    for word, cat in CATEGORY_WORDS.items():
        if word in t:
            args["category"] = cat
            break
    if re.search(r"navegador|browser|sin instalar", t):
        args["platform"] = "browser"
    elif re.search(r"\bpc\b|windows|computadora|ordenador", t):
        args["platform"] = "pc"
    if re.search(r"reciente|nuevo|nueva|antiguo|latest|newest", t):
        args["sort_by"] = "release-date"
    elif re.search(r"popular|conocid|famos", t):
        args["sort_by"] = "popularity"
    return args


class MockProvider:
    async def stream(self, messages: list[dict]) -> AsyncIterator[ProviderEvent]:
        last = messages[-1]
        if last["role"] == "tool":
            try:
                data = json.loads(last["content"])
            except json.JSONDecodeError:
                data = {"error": "bad tool output"}
            games = data.get("games") or ([data] if "title" in data else [])
            if data.get("error") or not games:
                text = "Modo demo (sin LLM real): no encontré juegos con esos criterios. Prueba con otra categoría."
            else:
                picks = ", ".join(f"{g['title']} ({g.get('genre') or 'sin género'})" for g in games[:3])
                text = f"Modo demo (sin LLM real). Te recomiendo: {picks}."
            for word in text.split(" "):
                yield ProviderEvent("text", text=word + " ")
            return
        yield ProviderEvent("tool_call", tool_call=ToolCall("mock-call-1", "get_games_by_filter", parse_query(last.get("content") or "")))
