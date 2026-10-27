"""Fake FreeToGame API for offline dev / P1-01 verification (the real host may be unreachable).
Run:  python scripts/fake_freetogame.py [port=9000]   then set FREETOGAME_BASE_URL=http://localhost:9000/api
Mimics: GET /api/games?platform=&category=&sort-by=  and  GET /api/game?id=  (+ GET /__hits to count upstream calls,
POST /__down to simulate an outage, POST /__up to recover). Data is synthetic; shapes follow the real API.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

GENRES = ["MMORPG", "Shooter", "Strategy", "MOBA", "Racing", "Card Game", "Fantasy", "Fighting", "Sports", "Social"]
GAMES = [
    {
        "id": i, "title": f"Fake Game {i}", "thumbnail": f"https://example.test/t/{i}.jpg",
        "short_description": f"Synthetic {GENRES[i % 10]} game number {i}.", "game_url": f"https://example.test/play/{i}",
        "genre": GENRES[i % 10], "platform": "PC (Windows)" if i % 3 else "Web Browser", "publisher": "Fake Pub",
        "developer": "Fake Dev", "release_date": f"20{10 + i % 15}-0{1 + i % 9}-1{i % 9}",
        "freetogame_profile_url": f"https://example.test/g/{i}",
    }
    for i in range(1, 61)
]
STATE = {"hits": 0, "down": False}


class H(BaseHTTPRequestHandler):
    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def do_POST(self):
        STATE["down"] = self.path == "/__down"
        self._send(200, STATE)

    def do_GET(self):
        u = urlparse(self.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path == "/__hits":
            return self._send(200, STATE)
        STATE["hits"] += 1
        if STATE["down"]:
            return self._send(503, {"status": 0, "status_message": "down"})
        if u.path == "/api/games":
            g = GAMES
            if q.get("category"): g = [x for x in g if x["genre"].lower().replace(" game", "") == q["category"].lower() or q["category"].lower() in x["genre"].lower()]
            if q.get("platform") in ("pc", "browser"): g = [x for x in g if ("Browser" in x["platform"]) == (q["platform"] == "browser")]
            if q.get("sort-by") == "alphabetical": g = sorted(g, key=lambda x: x["title"])
            if q.get("sort-by") == "release-date": g = sorted(g, key=lambda x: x["release_date"], reverse=True)
            return self._send(200, g)
        if u.path == "/api/game":
            g = next((x for x in GAMES if str(x["id"]) == q.get("id")), None)
            if not g: return self._send(404, {"status": 0, "status_message": "Game not found"})
            return self._send(200, g | {"status": "Live", "description": "Long synthetic description.",
                "minimum_system_requirements": {"os": "Windows 10", "memory": "4 GB", "graphics": None},
                "screenshots": [{"id": 1, "image": "https://example.test/s/1.jpg"}]})
        self._send(404, {"error": "not found"})

    def log_message(self, *a): pass


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", int(sys.argv[1]) if len(sys.argv) > 1 else 9000), H).serve_forever()
