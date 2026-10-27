# Trazabilidad SRS → código

| Req. | Dónde | Estado |
|---|---|---|
| RF-1.1 catálogo grid | `routes/games.py`, `frontend/app/page.tsx`, `GameCard` | 🟡 sin E2E (P1-01/03/06) |
| RF-1.2 filtros | `schemas.py` (valores), `routes/games.py`, `Filters.tsx`, `lib/constants.ts` | ✅ 422 en valores inválidos (test) |
| RF-1.3 detalle | `GET /api/games/{id}`, `GameModal.tsx` | 🟡 (P1-08) |
| RF-1.4 biblioteca | `routes/interactions.py` (+`GET /api/library`) | 🟡 semántica pendiente (P1-05) |
| RF-2.1/2.2 LLM + tools | `llm/tools.py`, `llm/orchestrator.py`, `llm/providers.py` | ✅ lógica con proveedor falso; 🟡 sin LLM real (P2-01) |
| RF-2.3 tarjetas en chat | evento SSE `games`, `ChatWidget.tsx` | 🟡 (P2-03) |
| RF-2.4 contexto | `services/chat_store.py`, `routes/chat.py` | 🟡 Postgres sí; Redis y UI de historial no (P2-05/06) |
| RF-3.1 batch 00:00 UTC | `ml/scheduler.py`, `ml/pipeline.py` | 🟡 sin probar con BD (P3-03) |
| RF-3.2 atributos | interacciones ✅ (`build_profile`); preferencias de chat: lectura sí, escritura no | 🟡 (P3-01) |
| RF-3.3 exclusión/diversidad | `ml/ranking.py` (`select_diverse`, exclusión) | ✅ tests; "subgénero"=género (D-07, Q-02) |
| RF-3.4 widget | `routes/recommendations.py`, `Top5Widget.tsx` | 🟡 (P3-04) |
| RNF-1 latencia | SSE implementado; medición pendiente | ⬜ (P2-01, Q-05) |
| RNF-2 caché 12 h | `core/cache.py`, `services/freetogame.py` | ✅ lógica con test; ⬜ Redis real (P1-01) |
| RNF-3 fallback | clave `:stale` (30 d) + tabla `games` en pipeline | ✅ lógica con test; ⬜ banner UI (P1-07) |
| RNF-4 secretos | `config.py` (env), frontend solo `NEXT_PUBLIC_API_URL` y user id de desarrollo | ✅ por diseño; revisar P4-05 |
