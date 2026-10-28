"""Chatbot evaluation harness (P2-01 latency + P2-02 tool-use quality). STATUS: harness tested offline (tests/test_eval_harness.py);
the REAL run needs an LLM key and is the owner's step.

Usage (from backend/, inside Docker: `docker compose exec backend python -m evals.chat_eval`):
  python -m evals.chat_eval                    # provider from .env (LLM_PROVIDER + key), real FreeToGame catalog
  python -m evals.chat_eval --provider mock --offline   # plumbing self-test, no key, no internet
  python -m evals.chat_eval --only shooter-popular --verbose
  python -m evals.chat_eval --out evals/results.json    # also write full results (answers included)
Reports per case: tool/args checks, cards, first-token latency, tool time, total; then pass rate and RNF-1 p50/p95
(first token < 1.5 s, tool execution < 3.0 s; see Q-05 in docs/HANDOFF.md for how first token is defined with tools).
"Invented games" cannot be detected automatically: read the answers (--verbose) and check titles against the tool results.
"""
import argparse
import asyncio
import json
import sys
import time

from app.config import get_settings
from app.llm.orchestrator import run_chat
from app.llm.providers import get_provider
from evals.cases import CASES

RNF1_FIRST_TOKEN_S = 1.5
RNF1_TOOL_S = 3.0


def score_case(expect: dict, tool_calls: list[dict]) -> dict[str, bool]:
    """Pure: which expectations hold for the tool calls of the last turn ([{name, arguments}])."""
    want = expect.get("tool")
    if want is None:
        return {"no_tool": not tool_calls}
    matching = [c for c in tool_calls if c["name"] == want]
    checks = {"tool": bool(matching)}
    if matching:
        args = matching[0]["arguments"]
        if "category_any" in expect:
            checks["category"] = str(args.get("category") or "").lower() in expect["category_any"]
        for k in ("platform", "sort_by"):
            if k in expect:
                checks[k] = args.get(k) == expect[k]
    return checks


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    v = sorted(values)
    return v[min(len(v) - 1, round(p / 100 * (len(v) - 1)))]


class RecordingProvider:
    """Wraps a provider: records tool calls and when the first text arrives."""

    def __init__(self, inner):
        self.inner, self.tool_calls = inner, []

    async def stream(self, messages):
        async for ev in self.inner.stream(messages):
            if ev.type == "tool_call" and ev.tool_call:
                self.tool_calls.append({"name": ev.tool_call.name, "arguments": ev.tool_call.arguments})
            yield ev


class TimedClient:
    """Wraps the catalog client: accumulates time spent in tool execution."""

    def __init__(self, inner):
        self.inner, self.tool_ms = inner, 0.0

    async def _timed(self, coro):
        t = time.perf_counter()
        try:
            return await coro
        finally:
            self.tool_ms += (time.perf_counter() - t) * 1000

    async def get_games(self, *a, **k):
        return await self._timed(self.inner.get_games(*a, **k))

    async def get_game(self, *a, **k):
        return await self._timed(self.inner.get_game(*a, **k))


async def run_case(case: dict, provider, client) -> dict:
    history: list[dict] = []
    res: dict = {"id": case["id"]}
    for i, turn in enumerate(case["turns"]):
        rec, timed = RecordingProvider(provider), TimedClient(client)
        t0 = time.perf_counter()
        first_event = first_token = None
        text, cards, error = [], [], None
        new_messages: list[dict] = []
        async for ev in run_chat(rec, timed, history, turn):
            now = time.perf_counter() - t0
            if ev["type"] in ("token", "tool_call") and first_event is None:
                first_event = now
            if ev["type"] == "token":
                first_token = first_token if first_token is not None else now
                text.append(ev["text"])
            elif ev["type"] == "games":
                cards = [g.get("title") for g in ev["games"]]
            elif ev["type"] == "error":
                error = ev["message"]
            elif ev["type"] == "done":
                new_messages = ev["new_messages"]
        history += new_messages
        if i == len(case["turns"]) - 1:  # metrics + checks only for the last turn
            checks = score_case(case["expect"], rec.tool_calls)
            if error:
                checks["no_error"] = False
            res.update(
                tool_calls=rec.tool_calls, checks=checks, passed=all(checks.values()), cards=cards, error=error,
                answer="".join(text), first_event_s=first_event, first_token_s=first_token,
                tool_s=timed.tool_ms / 1000, total_s=time.perf_counter() - t0,
            )
    return res


def summarize(results: list[dict]) -> str:
    n = len(results)
    ok = sum(r["passed"] for r in results)
    ft = [r["first_token_s"] for r in results if r.get("first_token_s") is not None]
    fe = [r["first_event_s"] for r in results if r.get("first_event_s") is not None]
    tl = [r["tool_s"] for r in results if r["tool_calls"]]
    f = lambda x: "n/a" if x is None else f"{x:.2f}s"
    return "\n".join([
        f"Pass: {ok}/{n} ({100 * ok / max(n, 1):.0f}%)  [objetivo P2-02: >= 90%]",
        f"First token  p50={f(percentile(ft, 50))} p95={f(percentile(ft, 95))}  [RNF-1: < {RNF1_FIRST_TOKEN_S}s]",
        f"First event  p50={f(percentile(fe, 50))} p95={f(percentile(fe, 95))}  (tool_call o token: lo primero que ve el usuario, Q-05)",
        f"Tool exec    p50={f(percentile(tl, 50))} p95={f(percentile(tl, 95))}  [RNF-1: < {RNF1_TOOL_S}s]",
    ])


async def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", help="override LLM_PROVIDER (openai|anthropic|mock)")
    ap.add_argument("--offline", action="store_true", help="use the in-memory fake catalog (no internet)")
    ap.add_argument("--only", help="run a single case id")
    ap.add_argument("--verbose", action="store_true", help="print answers and tool calls")
    ap.add_argument("--out", help="write full JSON results here")
    a = ap.parse_args(argv)

    settings = get_settings()
    if a.provider:
        settings = settings.model_copy(update={"llm_provider": a.provider})
    key = {"openai": settings.openai_api_key, "anthropic": settings.anthropic_api_key, "mock": "n/a"}.get(settings.llm_provider, "")
    if not key:
        print(f"Falta la API key de '{settings.llm_provider}' (ponla en .env) o usa --provider mock.", file=sys.stderr)
        return 2
    provider = get_provider(settings)
    if a.offline:
        from tests.test_tools import FakeClient

        client = FakeClient(n=12)
    else:
        from app.services.freetogame import FreeToGameClient

        class NoCache:  # evals must hit the real API, not Redis
            async def get(self, k): return None
            async def get_stale(self, k): return None
            async def set(self, k, v, ttl): return None

        client = FreeToGameClient(settings.freetogame_base_url, NoCache(), 0)
    cases = [c for c in CASES if not a.only or c["id"] == a.only]
    results = []
    for c in cases:
        r = await run_case(c, provider, client)
        results.append(r)
        bad = [k for k, v in r["checks"].items() if not v]
        print(f"{'PASS' if r['passed'] else 'FAIL'}  {r['id']:<26} tools={[t['name'] for t in r['tool_calls']]} cards={len(r['cards'])} "
              f"1st={r['first_token_s'] if r['first_token_s'] is None else round(r['first_token_s'], 2)}s total={r['total_s']:.2f}s"
              + (f"  ✗{bad}" if bad else ""))
        if a.verbose:
            print(f"      args={[t['arguments'] for t in r['tool_calls']]}\n      answer={r['answer'][:400]!r}")
    print("\n" + summarize(results))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=2)
    if hasattr(client, "aclose"):
        await client.aclose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
