"""POST /api/chat -> SSE stream (RNF-1). STATUS: implemented, untested end-to-end (P2-04).
Wire format per event: `event: <type>\\ndata: <json without type>\\n\\n` (frontend/lib/api.ts parses exactly this).
Event order: session, then (tool_call | token)*, games?, done  -- or error (no done).
TODO(P2-06): GET /api/chat/{session_id}/messages for the UI to restore past conversations (RF-2.4).
TODO(P2-05): Redis hot cache of history (see services/chat_store.py).
"""
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user_id, get_ftg, get_llm_provider
from app.db.session import SessionLocal
from app.llm.orchestrator import run_chat
from app.schemas import ChatRequest
from app.services.chat_store import get_or_create_session, load_history, save_messages
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
