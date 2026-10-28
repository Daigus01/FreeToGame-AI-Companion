"""DB chat rows -> what the UI shows (RF-2.4, P2-06). Pure + tested (tests/test_chat_view.py).
Cards are not stored: they are rebuilt with the SAME rule as live turns (app/llm/cards.py): games from the tool
results of that turn whose title the assistant text mentions. Full data (thumbnail...) comes from the cached catalog."""
import json

from app.llm.cards import MAX_CARDS, select_cards


def to_ui_messages(rows, catalog: dict[int, dict]) -> list[dict]:
    out: list[dict] = []
    turn: dict = {"text": [], "pool": {}, "details": []}

    def hydrate(g: dict) -> dict:
        return catalog.get(g["id"]) or g

    def flush() -> None:
        text = "\n\n".join(t for t in turn["text"] if t).strip()
        if text:
            games = select_cards(text, turn["pool"], MAX_CARDS)
            if not games and len(turn["details"]) == 1:
                games = turn["details"]
            out.append({"role": "assistant", "text": text, "games": games})
        turn.update(text=[], pool={}, details=[])

    for r in rows:
        if r.sender == "user":
            flush()
            out.append({"role": "user", "text": r.content, "games": []})
        elif r.sender == "tool":
            try:
                data = json.loads(r.content)
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(data, dict) or data.get("error"):
                continue
            if isinstance(data.get("games"), list):
                for g in data["games"]:
                    if isinstance(g, dict) and "id" in g:
                        turn["pool"][g["id"]] = hydrate(g)
            elif "id" in data and "title" in data:  # get_game_details result
                turn["pool"][data["id"]] = hydrate(data)
                turn["details"] = [hydrate(data)]
        elif r.sender == "assistant" and r.content:
            turn["text"].append(r.content)
    flush()
    return out
