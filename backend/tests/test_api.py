"""HTTP-level tests with dependency overrides (no Postgres/Redis needed). Lifespan is NOT started."""
from fastapi.testclient import TestClient

from app.api.deps import get_ftg
from app.main import app
from tests.test_tools import FakeClient

app.dependency_overrides[get_ftg] = lambda: FakeClient(n=3)
client = TestClient(app)  # not used as context manager -> no lifespan


def test_filters_endpoint_matches_srs():
    j = client.get("/api/filters").json()
    assert j["platforms"] == ["pc", "browser", "all"] and "mmorpg" in j["categories"]
    assert "release-date" in j["sort_options"]


def test_list_and_detail():
    assert [g["title"] for g in client.get("/api/games", params={"platform": "pc"}).json()] == ["G1", "G2", "G3"]
    assert client.get("/api/games/2").json()["title"] == "G2"
    assert client.get("/api/games/99").status_code == 404


def test_invalid_filter_is_422():
    assert client.get("/api/games", params={"platform": "xbox"}).status_code == 422
    assert client.get("/api/games", params={"sort_by": "random"}).status_code == 422
