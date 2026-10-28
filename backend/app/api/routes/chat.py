"""POST /api/chat -> SSE stream (RNF-1). STATUS: implemented, untested end-to-end (P2-04).
Wire format per event: `event: <type>\\ndata: <json without type>\\n\\n` (frontend/lib/api.ts parses exactly this).
Event order: session, then (tool_call | token)*, games?, done  -- or error (no done).
History (RF-2.4, P2-06): GET /api/chat/sessions (own conversations, newest first) and
GET /api/chat/{session_id}/messages (404 if not yours) -> messages with rebuilt cards.
"""
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_ftg, get_llm_provider
from app.db.session import SessionLocal, get_session
from app.llm.orchestrator import run_chat
from app.schemas import ChatMessageOut, ChatRequest, ChatSessionOut
from app.services.chat_store import get_or_create_session, get_session_rows, list_sessions, load_history, save_messages
from app.services.chat_view import to_ui_messages
from app.services.freetogame import UpstreamUnavailable
from app.services.users import ensure_user

router = APIRouter(prefix="/api/chat", tags=["chat"])


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("")
async def chat(body: ChatRequest, user_id=Depends(get_current_user_id), ftg=Depends(get_ftg), provider=Depends(get_llm_provider)):
    async def stream():
        async with SessionLocal() as db:
            await ensure_user(db, user_id)
            sid = await get_or_create_session(db, user_id, body.session_id)
            await db.commit()
            history = await load_history(db, sid)
            yield sse("session", {"session_id": str(sid)})
            async for ev in run_chat(provider, ftg, history, body.message):
                if ev["type"] == "done":
                    await save_messages(db, sid, ev["new_messages"])
                    yield sse("done", {})
                else:
                    yield sse(ev["type"], {k: v for k, v in ev.items() if k != "type"})

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/sessions", response_model=list[ChatSessionOut])
async def sessions(user_id: UUID = Depends(get_current_user_id), db: AsyncSession = Depends(get_session)):
    return await list_sessions(db, user_id)


@router.get("/{session_id}/messages", response_model=list[ChatMessageOut])
async def session_messages(session_id: UUID, user_id: UUID = Depends(get_current_user_id),
                           db: AsyncSession = Depends(get_session), ftg=Depends(get_ftg)):
    rows = await get_session_rows(db, user_id, session_id)
    if rows is None:
        raise HTTPException(404, "Session not found")
    try:
        catalog = {g["id"]: g for g in await ftg.get_games() if "id" in g}
    except UpstreamUnavailable:
        catalog = {}  # cards fall back to the slim data stored in tool messages
    return to_ui_messages(rows, catalog)
