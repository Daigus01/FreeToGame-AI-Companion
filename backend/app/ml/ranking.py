"""Pure (DB-free) ranking logic for the daily Top 5 (RF-3.2, RF-3.3). Easy to unit test.

STATUS: baseline content-based scorer implemented + tested (tests/test_ranking.py).
This is deliberately simple (genre/platform affinity + popularity prior). It is the cold-start-safe
baseline; replace/augment with `implicit` / LightGBM once there is interaction data (TODO P3-06).
DECISION D-07: the FreeToGame API exposes only `genre` (no sub-genre). RF-3.3's "max 2 per subgenre"
is therefore enforced on `genre` for now (constant MAX_PER_GENRE). Revisit if tags are fetched.
"""
from collections import defaultdict
from dataclasses import dataclass, field

TOP_N = 5
MAX_PER_GENRE = 2

# Implicit feedback weights per interaction type. played/disliked are exclusions (RF-3.3) and also
# shape the profile: disliked pushes its genre down; played is neutral-positive signal.
INTERACTION_WEIGHTS = {"view": 1.0, "click": 2.0, "saved": 5.0, "played": 1.0, "disliked": -4.0}


@dataclass
class Candidate:
    id: int
    genre: str | None
    platform: str | None
    popularity_rank: int  # 0 = most popular


@dataclass
class UserProfile:
    genre_affinity: dict[str, float] = field(default_factory=dict)
    platform_affinity: dict[str, float] = field(default_factory=dict)
    excluded_ids: set[int] = field(default_factory=set)


def build_profile(
    interactions: list[tuple[int, str]],  # (game_id, interaction_type)
    games_by_id: dict[int, Candidate],
    chat_preferences: dict | None = None,  # {"genres": {"mmorpg": 0.8}, "platform": "pc"}  (RF-3.2, TODO P3-01)
) -> UserProfile:
    p = UserProfile()
    genre: dict[str, float] = defaultdict(float)
    platform: dict[str, float] = defaultdict(float)
    for game_id, kind in interactions:
        if kind in ("played", "disliked"):
            p.excluded_ids.add(game_id)
        g = games_by_id.get(game_id)
        w = INTERACTION_WEIGHTS.get(kind, 0.0)
        if g and w:
            if g.genre:
                genre[g.genre] += w
            if g.platform:
                platform[g.platform] += w
    if chat_preferences:
        for name, score in (chat_preferences.get("genres") or {}).items():
            genre[name] += 5.0 * float(score)  # chat intent weighted like a "saved"
        if chat_preferences.get("platform"):
            platform[chat_preferences["platform"]] += 3.0
    p.genre_affinity, p.platform_affinity = dict(genre), dict(platform)
    return p


def score(c: Candidate, p: UserProfile, catalog_size: int) -> float:
    s = p.genre_affinity.get(c.genre or "", 0.0) + 0.5 * p.platform_affinity.get(c.platform or "", 0.0)
    s += 1.0 * (1 - c.popularity_rank / max(catalog_size, 1))  # popularity prior in [0,1], also cold-start
    return s


def select_diverse(ranked: list[Candidate], n: int = TOP_N, max_per_genre: int = MAX_PER_GENRE) -> list[Candidate]:
    """RF-3.3 diversity: greedy pick in rank order; skip a candidate if its genre already hit the cap.
    If the cap leaves fewer than n picks, backfill from the skipped ones (we must always return n if possible)."""
    picked: list[Candidate] = []
    skipped: list[Candidate] = []
    counts: dict[str | None, int] = defaultdict(int)
    for c in ranked:
        if len(picked) == n:
            break
        if counts[c.genre] >= max_per_genre:
            skipped.append(c)
            continue
        picked.append(c)
        counts[c.genre] += 1
    for c in skipped:
        if len(picked) == n:
            break
        picked.append(c)
    return picked


def recommend(candidates: list[Candidate], profile: UserProfile, n: int = TOP_N) -> list[int]:
    eligible = [c for c in candidates if c.id not in profile.excluded_ids]  # RF-3.3 exclusion
    size = len(candidates)
    ranked = sorted(eligible, key=lambda c: score(c, profile, size), reverse=True)
    return [c.id for c in select_diverse(ranked, n)]
