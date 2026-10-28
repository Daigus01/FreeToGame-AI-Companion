"""Chat history persistence (RF-2.4). STATUS: Postgres only; verified end-to-end with the mock provider (P2-04).
No Redis hot cache on purpose: the history query is one indexed read of <=30 rows (D-13); revisit if measured slow.

Conversion between DB rows and OpenAI-format messages (convention D-06):
  user row       sender='user'       content=text
  assistant row  sender='assistant'  content=text ('' if only tool calls), tool_calls={"tool_calls":[openai tool_call objs]}
  tool row       sender='tool'       content=json str, tool_calls={"tool_call_id": "..."}
TODO(P2-05): hot cache in Redis (last N messages per session) to cut latency (RNF-1); trim history by tokens.
"""
from uuid import UUID

from sqlalchemy import func, select
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


async def list_sessions(db: AsyncSession, user_id: UUID, limit: int = 20) -> list[dict]:
    """User's conversations that have at least one message, newest activity first. title = first user message."""
    first_user = (
        select(ChatMessage.content)
        .where(ChatMessage.session_id == ChatSession.id, ChatMessage.sender == "user")
        .order_by(ChatMessage.created_at)
        .limit(1)
        .scalar_subquery()
    )
    last_at = select(func.max(ChatMessage.created_at)).where(ChatMessage.session_id == ChatSession.id).scalar_subquery()
    rows = await db.execute(
        select(ChatSession.id, first_user.label("title"), last_at.label("updated_at"))
        .where(ChatSession.user_id == user_id, last_at.is_not(None))
        .order_by(last_at.desc())
        .limit(limit)
    )
    return [{"id": str(r.id), "title": (r.title or "")[:80], "updated_at": r.updated_at.isoformat()} for r in rows]


async def get_session_rows(db: AsyncSession, user_id: UUID, session_id: UUID) -> list[ChatMessage] | None:
    """All messages of a session in order, or None if the session does not exist or is not the user's."""
    session = await db.get(ChatSession, session_id)
    if session is None or session.user_id != user_id:
        return None
    result = await db.execute(select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at))
    return list(result.scalars().all())
