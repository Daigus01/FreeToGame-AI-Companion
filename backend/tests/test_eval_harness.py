"""The eval harness itself (P2-02). Real LLM runs are the owner's step; here we test scoring, dataset and plumbing."""
import asyncio

from app.llm.mock import MockProvider
from evals.cases import CASES
from evals.chat_eval import percentile, run_case, score_case, summarize
from tests.test_tools import FakeClient

F = "get_games_by_filter"


def test_score_case():
    exp = {"tool": F, "category_any": ["mmorpg", "fantasy"], "platform": "pc", "sort_by": "release-date"}
    ok = [{"name": F, "arguments": {"category": "MMORPG", "platform": "pc", "sort_by": "release-date"}}]
    assert all(score_case(exp, ok).values())
    bad = [{"name": F, "arguments": {"category": "shooter", "platform": "all"}}]
    assert score_case(exp, bad) == {"tool": True, "category": False, "platform": False, "sort_by": False}
    assert score_case(exp, []) == {"tool": False}
    assert score_case({"tool": None}, []) == {"no_tool": True} and score_case({"tool": None}, ok) == {"no_tool": False}


def test_dataset_is_well_formed():
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids)) >= 20
    from app.schemas import CATEGORIES
    for c in CASES:
        assert c["turns"] and all(isinstance(t, str) and t for t in c["turns"])
        e = c["expect"]
        assert e["tool"] in (None, F, "get_game_details")
        assert e.get("platform", "pc") in ("pc", "browser", "all")
        assert e.get("sort_by", "popularity") in ("release-date", "popularity", "alphabetical", "relevance")
        assert all(cat == cat.lower() for cat in e.get("category_any", []))
    assert any(set(c["expect"].get("category_any", [])) & set(CATEGORIES) for c in CASES)


def test_percentile_and_summary():
    assert percentile([], 50) is None and percentile([5], 95) == 5
    assert percentile([1, 2, 3, 4, 100], 50) == 3 and percentile([1, 2, 3, 4, 100], 95) == 100
    r = [{"passed": True, "first_token_s": 0.4, "first_event_s": 0.1, "tool_calls": [1], "tool_s": 0.2}]
    assert "Pass: 1/1" in summarize(r)


def test_run_case_plumbing_with_mock_and_fake_catalog():
    case = next(c for c in CASES if c["id"] == "mmorpg-fantasy-pc-recent")
    r = asyncio.run(run_case(case, MockProvider(), FakeClient(n=12)))
    assert r["passed"] and r["cards"] == ["G1", "G2", "G3"] and r["tool_calls"][0]["arguments"]["platform"] == "pc"
    assert r["first_token_s"] is not None and r["first_event_s"] <= r["first_token_s"] <= r["total_s"] and r["tool_s"] >= 0


def test_multi_turn_case_only_scores_last_turn():
    case = {"id": "x", "turns": ["dame un shooter", "hola"], "expect": {"tool": None}}  # mock always calls a tool -> must FAIL
    r = asyncio.run(run_case(case, MockProvider(), FakeClient()))
    assert r["passed"] is False and r["checks"] == {"no_tool": False}
