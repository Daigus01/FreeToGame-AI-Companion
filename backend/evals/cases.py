"""Evaluation set for the chatbot (P2-02): 20 cases. `turns` run in one conversation; `expect` applies to the LAST turn.
expect.tool: tool name that must be called, or None = must NOT call any tool.
expect.category_any / platform / sort_by: checked on the first call of that tool (only keys present are checked)."""

F = "get_games_by_filter"
CASES: list[dict] = [
    {"id": "mmorpg-fantasy-pc-recent", "turns": ["Busco un MMORPG de fantasía para PC que no sea muy antiguo"],
     "expect": {"tool": F, "category_any": ["mmorpg", "fantasy"], "platform": "pc", "sort_by": "release-date"}},
    {"id": "shooter-popular", "turns": ["Dame los shooters más populares"], "expect": {"tool": F, "category_any": ["shooter"], "sort_by": "popularity"}},
    {"id": "racing-browser", "turns": ["¿Hay juegos de carreras que pueda jugar en el navegador?"], "expect": {"tool": F, "category_any": ["racing"], "platform": "browser"}},
    {"id": "strategy", "turns": ["Quiero un juego de estrategia"], "expect": {"tool": F, "category_any": ["strategy"]}},
    {"id": "card", "turns": ["Juegos de cartas coleccionables"], "expect": {"tool": F, "category_any": ["card"]}},
    {"id": "pvp-pc-alpha", "turns": ["Juegos pvp para pc, en orden alfabético"], "expect": {"tool": F, "category_any": ["pvp"], "platform": "pc", "sort_by": "alphabetical"}},
    {"id": "moba", "turns": ["Recomiéndame un MOBA"], "expect": {"tool": F, "category_any": ["moba"]}},
    {"id": "anime", "turns": ["¿Algún juego con estilo anime?"], "expect": {"tool": F, "category_any": ["anime"]}},
    {"id": "fighting", "turns": ["Busco juegos de peleas"], "expect": {"tool": F, "category_any": ["fighting"]}},
    {"id": "sports-pc", "turns": ["Juegos de deportes para PC"], "expect": {"tool": F, "category_any": ["sports"], "platform": "pc"}},
    {"id": "survival", "turns": ["Quiero un juego de supervivencia"], "expect": {"tool": F, "category_any": ["survival"]}},
    {"id": "battle-royale", "turns": ["¿Qué battle royale gratis hay?"], "expect": {"tool": F, "category_any": ["battle-royale"]}},
    {"id": "scifi", "turns": ["Algo de ciencia ficción"], "expect": {"tool": F, "category_any": ["sci-fi"]}},
    {"id": "social", "turns": ["Juegos sociales para pasar el rato con amigos"], "expect": {"tool": F, "category_any": ["social"]}},
    {"id": "vague", "turns": ["¿Qué juegos gratis me recomiendas?"], "expect": {"tool": F}},
    {"id": "english-shooter-pc", "turns": ["I want a fast-paced shooter on PC"], "expect": {"tool": F, "category_any": ["shooter"], "platform": "pc"}},
    {"id": "details-of-first", "turns": ["Dame shooters populares", "Cuéntame más del primero"], "expect": {"tool": "get_game_details"}},
    {"id": "followup-latest-no-tool", "turns": ["Busco juegos mmorpg para pc", "¿Y de esos, cuál es el más reciente?"], "expect": {"tool": None}},
    {"id": "greeting-no-tool", "turns": ["Hola, ¿qué puedes hacer?"], "expect": {"tool": None}},
    {"id": "off-topic-no-tool", "turns": ["¿Cuál es la capital de Francia?"], "expect": {"tool": None}},
]
