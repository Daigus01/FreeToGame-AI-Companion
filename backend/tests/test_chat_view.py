"""P2-06: rebuilding UI messages (with cards) from stored rows."""
import json
from types import SimpleNamespace as R

from app.services.chat_view import to_ui_messages

SLIM = lambda i, t: {"id": i, "title": t, "genre": "MMORPG"}
FULL = {1: {"id": 1, "title": "Alpha", "thumbnail": "http://t/1.jpg"}, 2: {"id": 2, "title": "Beta", "thumbnail": "http://t/2.jpg"}}


def rows(*items): return [R(sender=s, content=c) for s, c in items]


def test_turn_with_tool_rebuilds_cards_hydrated_from_catalog():
    r = rows(("user", "busco mmorpg"), ("assistant", ""), ("tool", json.dumps({"count": 2, "games": [SLIM(1, "Alpha"), SLIM(2, "Beta")]})),
             ("assistant", "Te recomiendo Beta."))
    out = to_ui_messages(r, FULL)
    assert [m["role"] for m in out] == ["user", "assistant"]
    assert out[1]["text"] == "Te recomiendo Beta." and out[1]["games"] == [FULL[2]]  # hydrated: has thumbnail


def test_falls_back_to_slim_when_catalog_missing_and_pools_do_not_leak_between_turns():
    r = rows(("user", "q1"), ("tool", json.dumps({"games": [SLIM(1, "Alpha")]})), ("assistant", "Alpha es genial."),
             ("user", "q2"), ("assistant", "Sin más datos, pero Alpha me gusta."))
    out = to_ui_messages(r, {})
    assert out[1]["games"] == [SLIM(1, "Alpha")]
    assert out[3]["games"] == []  # q2 had no tool results in its own turn


def test_details_fallback_errors_and_bad_json_ignored_and_text_merged():
    d = {"id": 2, "title": "Beta", "description": "x"}
    r = rows(("user", "detalle"), ("assistant", "Voy a mirar."), ("tool", json.dumps(d)), ("tool", "not json"), ("tool", json.dumps({"error": "x"})),
             ("assistant", "Listo, juégalo."))
    out = to_ui_messages(r, FULL)
    assert out[1]["text"] == "Voy a mirar.\n\nListo, juégalo." and out[1]["games"] == [FULL[2]]


def test_empty_and_user_only():
    assert to_ui_messages([], {}) == []
    assert to_ui_messages(rows(("user", "hola")), {}) == [{"role": "user", "text": "hola", "games": []}]
