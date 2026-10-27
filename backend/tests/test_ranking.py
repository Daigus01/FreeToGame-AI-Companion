"""Tests for RF-3.3 (exclusion + diversity) and basic personalisation."""
from app.ml.ranking import Candidate, build_profile, recommend, select_diverse


def make_catalog():
    genres = ["MMORPG"] * 6 + ["Shooter"] * 6 + ["Strategy"] * 3 + ["Racing"] * 3
    return [Candidate(i, g, "PC (Windows)", i) for i, g in enumerate(genres, start=1)]


def test_returns_exactly_five():
    cands = make_catalog()
    assert len(recommend(cands, build_profile([], {c.id: c for c in cands}))) == 5


def test_max_two_per_genre():
    cands = make_catalog()
    ids = recommend(cands, build_profile([], {c.id: c for c in cands}))
    by_id = {c.id: c for c in cands}
    counts: dict[str, int] = {}
    for i in ids:
        counts[by_id[i].genre] = counts.get(by_id[i].genre, 0) + 1
    assert max(counts.values()) <= 2


def test_excludes_played_and_disliked():
    cands = make_catalog()
    by_id = {c.id: c for c in cands}
    profile = build_profile([(1, "played"), (2, "disliked")], by_id)
    ids = recommend(cands, profile)
    assert 1 not in ids and 2 not in ids


def test_saved_genre_is_boosted():
    cands = make_catalog()
    by_id = {c.id: c for c in cands}
    saved = [(13, "saved"), (14, "saved"), (15, "saved")]  # Strategy games
    ids = recommend(cands, build_profile(saved, by_id))
    assert sum(1 for i in ids if by_id[i].genre == "Strategy") >= 1


def test_backfills_when_cap_leaves_too_few():
    cands = [Candidate(i, "MMORPG", "PC", i) for i in range(1, 8)]
    assert len(select_diverse(cands)) == 5  # all same genre -> backfill, still 5
