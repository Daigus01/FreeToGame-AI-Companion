"""Chat orchestration loop (RF-2.1..2.3). Pure async generator: no DB, no HTTP -> unit-testable.

STATUS: done + tested (tests/test_orchestrator.py, scripted fake provider). NOT yet run with a real LLM (P2-01).
Contract (consumed by api/routes/chat.py, which adds the `session` event and persists `new_messages`):
  {"type":"tool_call","name":str} | {"type":"token","text":str} | {"type":"games","games":[...]}
  | {"type":"error","message":str} | {"type":"done","new_messages":[openai-format msgs]}
Messages use the OpenAI chat format internally (D-02, D-06).
Cards (P2-03, D-12): only games whose exact title appears in the assistant's text (see app/llm/cards.py).
Fallback: if nothing is mentioned but the model fetched details of exactly one game, show that game.
History is trimmed to a size budget before each call (app/llm/history.py, P2-05, D-13).
"""
import json
import logging
from collections.abc import AsyncIterator

from app.llm.cards import MAX_CARDS, select_cards
from app.llm.history import trim_history
from app.llm.prompts import SYSTEM_PROMPT
from app.llm.providers import LLMProvider
from app.llm.tools import execute_tool

logger = logging.getLogger(__name__)

MAX_ROUNDS = 4  # LLM <-> tool iterations per user turn


async def run_chat(provider: LLMProvider, client, history: list[dict], user_message: str) -> AsyncIterator[dict]:
    new_messages: list[dict] = [{"role": "user", "content": user_message}]
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}, *trim_history(history), *new_messages]
    cards: dict[int, dict] = {}  # every game returned by a tool this turn (candidates, not yet cards)
    detail_games: list[dict] = []
    said: list[str] = []  # all assistant text of this turn
    try:
        finished = False
        for _ in range(MAX_ROUNDS):
            text: list[str] = []
            calls = []
            async for ev in provider.stream(messages):
                if ev.type == "text":
                    text.append(ev.text)
                    yield {"type": "token", "text": ev.text}
                elif ev.type == "tool_call" and ev.tool_call:
                    calls.append(ev.tool_call)
            said.append("".join(text))
            assistant: dict = {"role": "assistant", "content": "".join(text) or None}
            if calls:
                assistant["tool_calls"] = [
                    {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": json.dumps(c.arguments)}}
                    for c in calls
                ]
            messages.append(assistant)
            new_messages.append(assistant)
            if not calls:
                finished = True
                break
            for c in calls:
                yield {"type": "tool_call", "name": c.name}
                out = await execute_tool(client, c.name, c.arguments)
                for g in out.games:
                    cards.setdefault(g["id"], g)
                if c.name == "get_game_details" and out.games:
                    detail_games = out.games
                tool_msg = {"role": "tool", "tool_call_id": c.id, "content": out.content}
                messages.append(tool_msg)
                new_messages.append(tool_msg)
        if not finished:  # keep history valid (a tool result must be followed by an assistant message)
            fallback = "No pude completar la búsqueda. ¿Puedes reformular tu petición?"
            yield {"type": "token", "text": fallback}
            new_messages.append({"role": "assistant", "content": fallback})
    except Exception:  # noqa: BLE001 - never leak provider internals to the client
        logger.exception("chat turn failed")
        yield {"type": "error", "message": "El asistente no está disponible en este momento."}
        return
    shown = select_cards(" ".join(said), cards, MAX_CARDS)
    if not shown and len(detail_games) == 1:
        shown = detail_games
    if shown:
        yield {"type": "games", "games": shown}
    yield {"type": "done", "new_messages": new_messages}
