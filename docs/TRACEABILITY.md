# Trazabilidad SRS → código

| Req. | Dónde | Estado |
|---|---|---|
| RF-1.1 catálogo grid | `routes/games.py`, `frontend/app/page.tsx`, `GameCard` | ✅ verificado por el dueño con API real (419 juegos) en navegador |
| RF-1.2 filtros | `schemas.py` (valores), `routes/games.py`, `Filters.tsx`, `lib/constants.ts` | ✅ 422 en valores inválidos (test); UI verificada en navegador |
| RF-1.3 detalle | `GET /api/games/{id}`, `GameModal.tsx` | ✅ modal verificado en navegador; 404 real confirmado; pulido pendiente (P1-08) |
| RF-1.4 biblioteca | `routes/interactions.py` (+`GET /api/library`), requiere sesión; modal avisa si no hay login | 🟡 semántica pendiente (P1-05, Q-04) |
| RF-2.1/2.2 LLM + tools | `llm/tools.py`, `llm/orchestrator.py`, `llm/providers.py` (OpenAI, Anthropic, mock), `llm/prompts.py` | ✅ flujo completo verificado con `mock` (HTTP+SSE+Postgres+navegador); 🟡 sin LLM real (P2-01/02/07) |
| RF-2.3 juegos recomendados por el chat | `llm/cards.py` (D-12), evento SSE `games`, `ChatWidget.tsx` (`onSuggest`) → `app/page.tsx` (catálogo principal, D-16) | ✅ selección: tests; ✅ tarjetas en chat verificadas en navegador (sesión 8); 🟡 presentación en el catálogo (D-16): solo `tsc`, falta navegador (P2-11). Nota: el SRS dice «tarjetas dentro del flujo del chat»; D-16 lo cambia por decisión del dueño |
| RF-2.4 contexto | `services/chat_store.py`, `services/chat_view.py`, `llm/history.py`, `routes/chat.py`, `ChatWidget.tsx` | ✅ Postgres (sin caché Redis, D-13); seguimiento y restauración verificados con `mock`; seguimiento con LLM real pendiente (P2-02) |
| RF-3.1 batch 00:00 UTC | `ml/scheduler.py`, `ml/pipeline.py` | 🟡 pipeline verificado con Postgres; scheduler cron sin ejecutar (P3-03) |
| RF-3.2 atributos | interacciones ✅ (`build_profile`); preferencias de chat: lectura sí, escritura no | 🟡 (P3-01) |
| RF-3.3 exclusión/diversidad | `ml/ranking.py` (`select_diverse`, exclusión) | ✅ tests; "subgénero"=género (D-07, Q-02) |
| RF-3.4 widget | `routes/recommendations.py`, `Top5Widget.tsx` | 🟡 (P3-04) |
| RNF-1 latencia | SSE implementado; medición pendiente | ⬜ (P2-01, Q-05) |
| RNF-2 caché 12 h | `core/cache.py`, `services/freetogame.py` | ✅ verificado con Redis real: 2ª petición sin llamada upstream, TTL 43200 s, copia `:stale` 30 d |
| RNF-3 fallback | clave `:stale` (30 d) + tabla `games` en pipeline | ✅ verificado: con upstream caído sirve copia stale (200) y sin copia responde 503; ⬜ banner UI (P1-07) |
| RNF-4 secretos | `config.py` (env), frontend solo `NEXT_PUBLIC_API_URL` (y un user id de desarrollo opcional, vacío por defecto); client secrets OAuth y `SESSION_SECRET` solo en backend | ✅ por diseño; revisar P4-05 |
| (no-SRS) Auth | `auth/`, `api/routes/auth.py`, `api/deps.py`, `AuthButton.tsx`, migración 003 (D-11) | ✅ login real verificado por el dueño (2026-10-28) |
