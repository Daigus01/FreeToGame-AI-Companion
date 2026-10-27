"""Glue between API game dicts and the pure ranking module. STATUS: done."""
from app.ml.ranking import Candidate


def to_candidates(games_by_popularity: list[dict]) -> list[Candidate]:
    """Input must already be ordered most-popular first (FreeToGame sort-by=popularity)."""
    return [
        Candidate(id=g["id"], genre=g.get("genre"), platform=g.get("platform"), popularity_rank=i)
        for i, g in enumerate(games_by_popularity)
        if "id" in g
    ]
