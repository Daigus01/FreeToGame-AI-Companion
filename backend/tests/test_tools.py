"""Tool schema + executor tests. Also hosts `FakeClient`, imported by tests/test_orchestrator.py."""
import asyncio
import json

from app.llm import tools
from app.services.freetogame import UpstreamUnavailable


def make_game(i: int) -> dict:
    return {
        "id": i, "title": f"G{i}", "thumbnail": f"https://img/{i}.jpg", "short_description": f"desc {i}",
        "game_url": f"https://play/{i}", "genre": "MMORPG", "platform": "PC (Windows)", "publisher": "P",
        "developer": "D", "release_date": "2020-01-01", "freetogame_profile_url": f"https://ftg/{i}",
    }


class FakeClient:
    """Stands in for FreeToGameClient (same async method signatures)."""

    def __init__(self, n: int = 10, down: bool = False):
        self.games = [make_game(i) for i in range(1, n + 1)]
        self.down = down
        self.calls: list[tuple] = []

    async def get_games(self, category=None, platform=None, sort_by=None):
        if self.down:
            raise UpstreamUnavailable("/games")
        self.calls.append((category, platform, sort_by))
        return self.games

    async def get_game(self, game_id: int):
        if self.down:
            raise UpstreamUnavailable("/game")
        g = next((g for g in self.games if g["id"] == game_id), None)
        return None if g is None else g | {"description": "long text", "minimum_system_requirements": {"os": "Win"}, "screenshots": []}


def run(coro):
    return asyncio.run(coro)


def test_schemas_match_srs_section5():
    assert [s["name"] for s in tools.TOOL_SCHEMAS] == ["get_games_by_filter", "get_game_details"]
    props = tools.TOOL_SCHEMAS[0]["parameters"]["properties"]
    assert props["platform"]["enum"] == ["pc", "browser", "all"]
    assert props["sort_by"]["enum"] == ["release-date", "popularity", "alphabetical", "relevance"]
    assert tools.TOOL_SCHEMAS[1]["parameters"]["required"] == ["game_id"]


def test_converters():
    assert tools.to_openai_tools()[0]["type"] == "function"
    assert "input_schema" in tools.to_anthropic_tools()[1]


def test_filter_caps_results_and_returns_cards():
    c = FakeClient(n=30)
    out = run(tools.execute_tool(c, "get_games_by_filter", {"category": "mmorpg", "platform": "pc"}))
    payload = json.loads(out.content)
    assert payload["count"] == tools.MAX_TOOL_RESULTS == len(out.games)
    assert "thumbnail" not in payload["games"][0] and "thumbnail" in out.games[0]  # slim for LLM, full for UI
    assert c.calls == [("mmorpg", "pc", None)]


def test_bad_enum_returns_error_not_exception():
    out = run(tools.execute_tool(FakeClient(), "get_games_by_filter", {"platform": "xbox"}))
    assert "error" in json.loads(out.content) and out.games == []


def test_details_found_missing_and_bad_args():
    c = FakeClient()
    ok = run(tools.execute_tool(c, "get_game_details", {"game_id": 3}))
    assert json.loads(ok.content)["title"] == "G3" and ok.games[0]["id"] == 3
    assert "error" in json.loads(run(tools.execute_tool(c, "get_game_details", {"game_id": 999})).content)
    assert "error" in json.loads(run(tools.execute_tool(c, "get_game_details", {})).content)
    assert "error" in json.loads(run(tools.execute_tool(c, "nope", {})).content)


def test_upstream_down_is_reported_to_model():
    out = run(tools.execute_tool(FakeClient(down=True), "get_games_by_filter", {}))
    assert "no disponible" in json.loads(out.content)["error"]
