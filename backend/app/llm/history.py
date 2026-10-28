"""History size budget (P2-05, D-13). Pure + tested (tests/test_history.py).
Keeps the newest messages within a character budget (~4 chars/token). The kept window always starts at a USER
message: providers reject an assistant tool_call without its tool result, or a tool result without its call."""

MAX_HISTORY_CHARS = 24_000  # ≈ 6k tokens of past conversation


def _size(m: dict) -> int:
    n = len(m.get("content") or "")
    for tc in m.get("tool_calls") or []:
        fn = tc.get("function", {})
        n += len(fn.get("name", "")) + len(fn.get("arguments", ""))
    return n


def trim_history(history: list[dict], max_chars: int = MAX_HISTORY_CHARS) -> list[dict]:
    total = sum(_size(m) for m in history)
    i = 0
    while total > max_chars and i < len(history):
        total -= _size(history[i])
        i += 1
    while i < len(history) and history[i]["role"] != "user":
        i += 1
    return history[i:]
