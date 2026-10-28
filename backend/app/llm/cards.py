"""Which games become UI cards in the chat (RF-2.3, P2-03, D-12). Pure functions, unit-tested (tests/test_cards.py).

Rule: a game gets a card iff the assistant's text mentions its exact title (case-insensitive, whole-word) AND the
game came from a tool result in this conversation (so the model cannot summon cards for invented games).
Order = order of first mention. If a title is contained in a longer mentioned title ("Dota" vs "Dota 2") only the
longer one counts. The prompt tells the model to write titles exactly as returned by the tools.
"""
import re

MAX_CARDS = 6


def select_cards(text: str, candidates: dict[int, dict], limit: int = MAX_CARDS) -> list[dict]:
    low = (text or "").casefold()
    spans: list[tuple[int, int, int]] = []  # (start, end, game_id)
    for gid, g in candidates.items():
        title = (g.get("title") or "").strip().casefold()
        if not title:
            continue
        m = re.search(r"(?<!\w)" + re.escape(title) + r"(?!\w)", low)
        if m:
            spans.append((m.start(), m.end(), gid))
    # drop matches fully inside a longer match of another title
    kept = [s for s in spans if not any(o is not s and o[0] <= s[0] and s[1] <= o[1] and (o[1] - o[0]) > (s[1] - s[0]) for o in spans)]
    kept.sort(key=lambda s: s[0])
    return [candidates[gid] for _, _, gid in kept][:limit]
