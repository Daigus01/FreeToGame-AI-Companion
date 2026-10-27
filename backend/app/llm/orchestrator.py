"""Chat orchestration loop (RF-2.1..2.3). Pure async generator: no DB, no HTTP -> unit-testable.

STATUS: done + tested (tests/test_orchestrator.py, scripted fake provider). NOT yet run with a real LLM (P2-01).
Contract (consumed by api/routes/chat.py, which adds the `session` event and persists `new_messages`):
  {"type":"tool_call","name":str} | {"type":"token","text":str} | {"type":"games","games":[...]}
  | {"type":"error","message":str} | {"type":"done","new_messages":[openai-format msgs]}
Messages use the OpenAI chat format internally (D-02, D-06).
TODO(P2-03): cards are every game returned by tools (capped). Better: only games the model actually
             recommended (e.g. ask the model for ids in a final structured step) -> fewer irrelevant cards.
"""
import json
import logging
from collections.abc import AsyncIterator

from app.llm.prompts import SYSTEM_PROMPT
from app.llm.providers import LLMProvider
from app.llm.tools import execute_tool

logger = logging.getLogger(__name__)

MAX_ROUNDS = 4  # LLM <-> tool iterations per user turn
MAX_CARDS = 6


async def run_chat(provider: LLMProvider, client, history: list[dict], user_message: str) -> AsyncIterator[dict]:
    new_messages: list[dict] = [{"role": "user", "content": user_message}]
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}, *history, *new_messages]
    cards: dict[int, dict] = {}
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
    if cards:
        yield {"type": "games", "games": list(cards.values())[:MAX_CARDS]}
    yield {"type": "done", "new_messages": new_messages}
