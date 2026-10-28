"""P2-04: full chat turns through HTTP + SSE + real Postgres, with MockProvider and FakeClient (no LLM, no internet).
Auto-skipped when Postgres is unreachable or migrations are missing. Run in Docker: `docker compose exec backend python -m pytest -q`."""
import asyncio
import json
import uuid

import asyncpg
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_ftg
from app.auth.session import make_session
from app.config import get_settings
from app.llm.mock import MockProvider
from tests.test_tools import FakeClient

pytestmark = pytest.mark.integration
SECRET = "it-secret"


def _url() -> str:
    return get_settings().database_url.replace("postgresql+asyncpg://", "postgresql://")


async def _db_ready() -> bool:
    try:
        conn = await asyncpg.connect(_url(), timeout=2)
    except Exception:  # noqa: BLE001
        return False
    try:
        return bool(await conn.fetchval("select to_regclass('public.chat_messages') is not null"))
    finally:
        await conn.close()


async def _sql(query: str, *args):
    conn = await asyncpg.connect(_url(), timeout=5)
    try:
        return await conn.fetchval(query, *args)
    finally:
        await conn.close()


def parse_sse(text: str) -> list[tuple[str, dict]]:
    out = []
    for block in filter(None, text.split("\n\n")):
        ev = next(l[7:] for l in block.splitlines() if l.startswith("event: "))
        data = next(l[6:] for l in block.splitlines() if l.startswith("data: "))
        out.append((ev, json.loads(data)))
    return out


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("ENABLE_SCHEDULER", "false")
    monkeypatch.setenv("SESSION_SECRET", SECRET)
    monkeypatch.setenv("ALLOW_DEV_AUTH", "false")
    get_settings.cache_clear()
    if not asyncio.run(_db_ready()):
        get_settings.cache_clear()
        pytest.skip("Postgres with migrations not reachable")
    from app.main import app

    app.dependency_overrides[get_ftg] = lambda: FakeClient()
    users = []

    async def new_user() -> uuid.UUID:
        uid = uuid.uuid4()
        await _sql("insert into users(id,email) values($1,$2) returning 1", uid, f"{uid}@it.test")
        users.append(uid)
        return uid

    with TestClient(app) as client:
        app.state.provider = MockProvider()
        yield client, new_user
    for uid in users:
        asyncio.run(_sql("delete from users where id=$1 returning 1", uid))
    app.dependency_overrides.pop(get_ftg, None)
    get_settings.cache_clear()


def as_user(client: TestClient, uid: uuid.UUID) -> None:
    client.cookies.set("ftg_session", make_session(uid, SECRET))


def test_chat_roundtrip_persistence_followup_and_isolation(api):
    client, new_user = api
    assert client.post("/api/chat", json={"message": "hola"}).status_code == 401  # no session

    alice = asyncio.run(new_user())
    as_user(client, alice)
    r = client.post("/api/chat", json={"message": "dame un mmorpg para pc"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    ev = parse_sse(r.text)
    types = [e for e, _ in ev]
    assert types[:2] == ["session", "tool_call"] and types[-2:] == ["games", "done"] and "token" in types
    sid = ev[0][1]["session_id"]
    assert [g["title"] for g in ev[-2][1]["games"]] == ["G1", "G2", "G3"]

    sessions = client.get("/api/chat/sessions").json()
    assert [s["id"] for s in sessions] == [sid] and sessions[0]["title"] == "dame un mmorpg para pc"

    msgs = client.get(f"/api/chat/{sid}/messages").json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert [g["title"] for g in msgs[1]["games"]] == ["G1", "G2", "G3"] and msgs[1]["games"][0]["thumbnail"]  # rebuilt + hydrated

    # follow-up in the same session: history is loaded and appended
    ev2 = parse_sse(client.post("/api/chat", json={"message": "ahora un shooter", "session_id": sid}).text)
    assert ev2[0] == ("session", {"session_id": sid})
    assert len(client.get(f"/api/chat/{sid}/messages").json()) == 4

    # another user can neither read nor continue Alice's session
    bob = asyncio.run(new_user())
    as_user(client, bob)
    assert client.get(f"/api/chat/{sid}/messages").status_code == 404
    assert client.get("/api/chat/sessions").json() == []
    other = parse_sse(client.post("/api/chat", json={"message": "hola", "session_id": sid}).text)
    assert other[0][1]["session_id"] != sid  # a fresh session was created for Bob


def test_provider_failure_emits_error_and_persists_nothing(api):
    client, new_user = api

    class Boom:
        async def stream(self, messages):
            raise RuntimeError("secret internal detail")
            yield  # pragma: no cover

    client.app.state.provider = Boom()
    as_user(client, asyncio.run(new_user()))
    ev = parse_sse(client.post("/api/chat", json={"message": "hola"}).text)
    assert [e for e, _ in ev] == ["session", "error"] and "secret" not in json.dumps(ev)
    assert client.get("/api/chat/sessions").json() == []  # empty session hidden, nothing stored
