"""LLM tool schemas (SRS section 5, verbatim semantics) + executor.

STATUS: done + tested (tests/test_tools.py). Schemas are provider-neutral JSON Schema; converters adapt them.
Design notes:
  - `execute_tool` NEVER raises: errors come back as {"error": ...} so the model can recover (RF-2.2).
  - The model sees a SLIM payload (tokens/latency, RNF-1); the UI cards get the fuller `games` list.
  - Tool output is untrusted data (see prompts.py).
"""
import json
from dataclasses import dataclass, field
from typing import Any, get_args

from app.schemas import GameSummary, Platform, SortBy
from app.services.freetogame import UpstreamUnavailable

MAX_TOOL_RESULTS = 12

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "get_games_by_filter",
        "description": "Consulta el catálogo de juegos de FreeToGame aplicando filtros por categoría, plataforma o criterio de ordenamiento.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Categoría o género principal del juego (ej. 'shooter', 'mmorpg', 'pvp', 'strategy', 'racing', 'anime', 'fantasy')."},
                "platform": {"type": "string", "enum": ["pc", "browser", "all"], "description": "Plataforma en la que se ejecuta el juego."},
                "sort_by": {"type": "string", "enum": ["release-date", "popularity", "alphabetical", "relevance"], "description": "Criterio de ordenamiento de los resultados."},
            },
            "required": [],
        },
    },
    {
        "name": "get_game_details",
        "description": "Obtiene la información detallada e id de un videojuego específico.",
        "parameters": {
            "type": "object",
            "properties": {"game_id": {"type": "integer", "description": "ID único del videojuego en FreeToGame."}},
            "required": ["game_id"],
        },
    },
]


def to_openai_tools() -> list[dict]:
    return [{"type": "function", "function": s} for s in TOOL_SCHEMAS]


def to_anthropic_tools() -> list[dict]:
    return [{"name": s["name"], "description": s["description"], "input_schema": s["parameters"]} for s in TOOL_SCHEMAS]


@dataclass
class ToolOutput:
    content: str  # JSON string fed back to the LLM
    games: list[dict] = field(default_factory=list)  # GameSummary-shaped dicts for UI cards (RF-2.3)


_CARD_FIELDS = list(GameSummary.model_fields)


def _card(g: dict) -> dict:
    return {k: g.get(k) for k in _CARD_FIELDS if k in g}


def _slim(g: dict) -> dict:
    out = {k: g.get(k) for k in ("id", "title", "genre", "platform", "release_date", "publisher", "developer")}
    out["short_description"] = (g.get("short_description") or "")[:140]
    return out


def _dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


async def execute_tool(client, name: str, args: dict) -> ToolOutput:
    try:
        if name == "get_games_by_filter":
            platform, sort_by = args.get("platform"), args.get("sort_by")
            if platform is not None and platform not in get_args(Platform):
                return ToolOutput(_dump({"error": f"platform inválida: {platform!r}. Usa pc, browser o all."}))
            if sort_by is not None and sort_by not in get_args(SortBy):
                return ToolOutput(_dump({"error": f"sort_by inválido: {sort_by!r}. Usa {list(get_args(SortBy))}."}))
            games = (await client.get_games(args.get("category"), platform, sort_by))[:MAX_TOOL_RESULTS]
            return ToolOutput(_dump({"count": len(games), "games": [_slim(g) for g in games]}), [_card(g) for g in games])
        if name == "get_game_details":
            game = await client.get_game(int(args["game_id"]))
            if game is None:
                return ToolOutput(_dump({"error": "juego no encontrado"}))
            slim = _slim(game) | {
                "description": (game.get("description") or "")[:600],
                "minimum_system_requirements": game.get("minimum_system_requirements"),
            }
            return ToolOutput(_dump(slim), [_card(game)])
        return ToolOutput(_dump({"error": f"herramienta desconocida: {name}"}))
    except UpstreamUnavailable:
        return ToolOutput(_dump({"error": "catálogo no disponible temporalmente"}))
    except (KeyError, TypeError, ValueError) as e:
        return ToolOutput(_dump({"error": f"argumentos inválidos: {e}"}))
