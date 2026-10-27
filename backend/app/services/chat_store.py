"""Chat history persistence (RF-2.4). STATUS: implemented in Postgres only, untested (P2-05).

Conversion between DB rows and OpenAI-format messages (convention D-06):
  user row       sender='user'       content=text
  assistant row  sender='assistant'  content=text ('' if only tool calls), tool_calls={"tool_calls":[openai tool_call objs]}
  tool row       sender='tool'       content=json str, tool_calls={"tool_call_id": "..."}
TODO(P2-05): hot cache in Redis (last N messages per session) to cut latency (RNF-1); trim history by tokens.
"""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatMessage, ChatSession

HISTORY_LIMIT = 30


async def get_or_create_session(db: AsyncSession, user_id: UUID, session_id: UUID | None) -> UUID:
    if session_id:
        row = await db.get(ChatSession, session_id)
        if row and row.user_id == user_id:  # never let a user read another user's session
            return row.id
    row = ChatSession(user_id=user_id)
    db.add(row)
    await db.flush()
    return row.id


async def load_history(db: AsyncSession, session_id: UUID) -> list[dict]:
    rows = (
        (
            await db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id, ChatMessage.sender != "system")
                .order_by(ChatMessage.created_at.desc())
                .limit(HISTORY_LIMIT)
            )
        )
        .scalars()
        .all()
    )
    msgs: list[dict] = []
    for r in reversed(rows):
        if r.sender == "tool":
            msgs.append({"role": "tool", "tool_call_id": (r.tool_calls or {}).get("tool_call_id", ""), "content": r.content})
        elif r.sender == "assistant":
            m: dict = {"role": "assistant", "content": r.content or None}
            if r.tool_calls and r.tool_calls.get("tool_calls"):
                m["tool_calls"] = r.tool_calls["tool_calls"]
            msgs.append(m)
        else:
            msgs.append({"role": "user", "content": r.content})
    # A truncated window may start with orphan tool messages, which providers reject. Drop them.
    while msgs and msgs[0]["role"] == "tool":
        msgs.pop(0)
    return msgs


async def save_messages(db: AsyncSession, session_id: UUID, new_messages: list[dict]) -> None:
    for m in new_messages:
        role = m["role"]
        extra = None
        if role == "tool":
            extra = {"tool_call_id": m["tool_call_id"]}
        elif role == "assistant" and m.get("tool_calls"):
            extra = {"tool_calls": m["tool_calls"]}
        db.add(ChatMessage(session_id=session_id, sender=role, content=m.get("content") or "", tool_calls=extra))
    await db.commit()
