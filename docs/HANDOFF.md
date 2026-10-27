# HANDOFF — estado del proyecto y guía para retomarlo con otra IA

## 1. Resumen de estado (2026-10-27)
Esqueleto funcional de las 3 fases del SRS. Backend: 20 tests en verde (sin servicios externos). Frontend: `tsc` limpio.
Verificado con Postgres 16 y Redis 7 reales (sesión 3): migraciones, `/health`, caché 12 h, copia stale, `catalog_sync`, interacciones y pipeline diario. `docker compose up` y `catalog_sync` con la API real de FreeToGame (419 juegos) fueron ejecutados por el dueño en Windows (sesión 4). **Sigue sin verificarse:** detalle/404 de la API real, el frontend en navegador y un LLM real. Lo marcado 🟡 en ROADMAP.md está parcialmente verificado; lee su nota.
Siguiente paso recomendado: P1-06 (abrir el frontend en el navegador y revisar catálogo/filtros/modal) + resto de P1-03 → P1-04 (auth, tras Q-01) → programar `catalog_sync` (P1-02) → Fase 2.

## 2. Cómo retomar (prompt sugerido para la IA auxiliar)
> Lee `CLAUDE.md`, `docs/HANDOFF.md`, `docs/ROADMAP.md` y la última entrada de `docs/PROGRESS.md`. Ejecuta `make test` y `make typecheck` para confirmar el estado base. Toma la primera tarea ⬜/🟡 del ROADMAP de la fase actual, impleméntala con tests, y al terminar actualiza ROADMAP (estado), PROGRESS (entrada nueva), TRACEABILITY si aplica y los `STATUS:`/`TODO(ID)` del código. No sobrescribas archivos existentes sin leerlos. Si hay una decisión de producto abierta (sección 5), pregunta antes de decidir.

## 3. Mapa del código
```
backend/app/
  main.py              wiring FastAPI + lifespan (redis, cliente FTG, scheduler)
  config.py            Settings / get_settings()  (env vars; ver .env.example)
  schemas.py           Pydantic + enums (fuente única de filtros RF-1.2)
  core/cache.py        JsonCache: clave fresca (TTL 12h) + clave ':stale' (30d) para modo degradado
  services/freetogame.py  cliente API externa (caché + stale fallback; UpstreamUnavailable)
  services/catalog_sync.py  API → tabla games (python -m app.services.catalog_sync)
  services/chat_store.py    historial en Postgres (convención D-06)
  services/recs.py / users.py  glue ranking / crear usuario dev
  api/deps.py          get_ftg, get_current_user_id (STUB dev), get_llm_provider
  api/routes/          health, games(+filters), interactions(+library), chat(SSE), recommendations
  llm/tools.py         schemas SRS §5 + execute_tool (nunca lanza; devuelve {"error"})
  llm/orchestrator.py  run_chat(): bucle LLM↔tools (máx 4 rondas), eventos token/tool_call/games/error/done
  llm/providers.py     OpenAIProvider (streaming), AnthropicProvider (stub)
  llm/prompts.py       SYSTEM_PROMPT
  ml/ranking.py        PURO: build_profile, score, select_diverse, recommend (RF-3.2/3.3)
  ml/pipeline.py       batch diario → daily_recommendations (upsert idempotente)
  ml/scheduler.py      APScheduler cron 00:00 UTC
  db/models.py, db/session.py   SQLAlchemy async
backend/migrations/    001_init.sql (SRS §6 + índices), 002_preference_profiles.sql (extensión)
backend/scripts/       fake_freetogame.py (API falsa para desarrollo offline; ver §8)
backend/tests/         test_tools (aloja FakeClient), test_orchestrator, test_ranking, test_freetogame_client, test_api
frontend/app/          layout.tsx, page.tsx
frontend/components/   GameCard, Filters, GameModal, Top5Widget, ChatWidget
frontend/lib/          api.ts (cliente + streamChat SSE), types.ts, constants.ts
```

## 4. Decisiones (D-xx)
- **D-01** Stack: FastAPI (Python) + Next.js/Tailwind + Postgres + Redis, elegido entre las opciones del SRS §2.2. *(Numeración reconstruida tras el incidente I-01.)*
- **D-02** Mensajes en formato OpenAI internamente; los proveedores traducen. Orquestador depende solo de `LLMProvider`.
- **D-03** SSE sobre `fetch` con POST (EventSource no admite POST). *(Reconstruida desde `lib/api.ts`; el texto original no se conserva.)*
- **D-04** El SQL en `backend/migrations/` es el esquema canónico; los modelos SQLAlchemy se sincronizan a mano. Sin Alembic por ahora (se aplican al primer arranque de Postgres vía docker).
- **D-05** Extensión al SRS: tabla `user_preference_profiles` (JSONB) para guardar preferencias extraídas del chat (RF-3.2).
- **D-06** Convención de `chat_messages`: fila assistant → `tool_calls={"tool_calls":[...]}`; fila tool → `tool_calls={"tool_call_id":...}`.
- **D-07** La API solo expone `genre`; "máx. 2 por subgénero" (RF-3.3) se aplica sobre `genre` (`MAX_PER_GENRE`). Ver Q-02.
- **D-08** Scheduler en proceso (APScheduler) para 1 réplica; con varias, mover a worker dedicado o Celery beat. `ENABLE_SCHEDULER=false` lo apaga.
- **D-09** Las herramientas devuelven al LLM una carga *reducida* (id, título, género…, descripción 140 car., máx. 12 juegos) y a la UI los datos completos para tarjetas, para ahorrar tokens/latencia (RNF-1).
- **D-10** Un fallo del proveedor LLM produce un evento SSE `error` genérico (sin detalles internos) y no persiste el turno.

## 5. Preguntas abiertas (necesitan al dueño del producto)
- **Q-01 Auth:** el SRS lista "Auth & User Service" sin requisitos. ¿Email magic link, OAuth, usuario/contraseña? Hoy: stub `X-User-Id` (solo desarrollo). Bloquea P1-04.
- **Q-02 "Subgénero":** la API no lo da. ¿Basta `genre`, o se enriquecen con etiquetas/categorías (`?category=` por etiqueta)? Afecta P3-07.
- **Q-03 Proveedor/modelo LLM y presupuesto:** el SRS cita GPT-4o-mini / "Claude 3.5 Sonnet" (ya antiguos). Los modelos son configurables por env; falta elegir default y límite de gasto por usuario.
- **Q-04 Semántica de biblioteca:** ¿"guardado/jugado/no me interesa" son estados excluyentes (último gana, se puede deshacer) o eventos acumulativos? Hoy: solo se añaden filas.
- **Q-05 RNF-1:** "primer token < 1.5 s" choca con el flujo con herramientas (LLM → tool → LLM). Propuesta: contar el evento `tool_call` (estado "Consultando catálogo…") como primer feedback, o medir primer token *de texto* solo en turnos sin tool. Confirmar criterio.

## 6. Contrato SSE de `POST /api/chat`
Petición: `{"message": str(1..2000), "session_id": uuid|null}` (+ cabecera `X-User-Id` en modo dev).
Cada evento: `event: <tipo>\ndata: <json en una línea>\n\n`. Orden: `session` → (`tool_call` | `token`)* → `games`? → `done`; o `error` (sin `done`).
| evento | data |
|---|---|
| session | `{"session_id": "<uuid>"}` |
| token | `{"text": "..."}` |
| tool_call | `{"name": "get_games_by_filter"}` |
| games | `{"games": [GameSummary,...]}` (máx. 6) |
| error | `{"message": "..."}` |
| done | `{}` |
Espejo TypeScript: `frontend/lib/types.ts` (`ChatEvent`). Si cambias uno, cambia el otro y `ChatWidget.tsx`.

## 7. Notas sobre el SRS
- `platform=all` y `sort-by` (con guion) son los nombres reales de la API; nuestra API pública usa `sort_by`.
- Los filtros de UI (RF-1.2) son un subconjunto de las categorías reales de FreeToGame; las tools aceptan cualquier categoría.
- El SRS no define auth, paginación, ni cómo se decide qué juegos mostrar como tarjeta (ver P2-03).
- `docs/SRS.md` es copia exacta del SRS recibido.

## 8. Entorno y límites conocidos
- Python 3.12 en Docker (en el sandbox de desarrollo corrió 3.13). Dependencias: `backend/requirements.txt`.
- Tests no necesitan Postgres/Redis: usan `FakeClient`, `httpx.MockTransport` y overrides de FastAPI. `db/session.py` crea el engine al importar pero no conecta.
- `db/session.py` y `services/catalog_sync.py` requieren Postgres vivo para ejecutarse de verdad.
- El historial pasado a proveedor puede crecer: hoy se limita a 30 mensajes (`HISTORY_LIMIT`); recorte por tokens pendiente (P2-05).
- **API falsa para desarrollo offline:** `python backend/scripts/fake_freetogame.py 9000` y `FREETOGAME_BASE_URL=http://localhost:9000/api`. Endpoints extra: `GET /__hits` (cuenta llamadas), `POST /__down` / `POST /__up` (simula caída). Datos sintéticos (60 juegos); no sustituye P1-03.
- **Arranque local sin Docker** (así se verificó en la sesión 3): Postgres 16 + Redis 7 locales, aplicar `backend/migrations/*.sql` en orden, `ENABLE_SCHEDULER=false`, `uvicorn app.main:app`. Cuidado: `pkill -f uvicorn` desde un shell cuyo comando contenga ese texto lo mata a sí mismo.
- El cliente trata HTTP 404 de FreeToGame como "no encontrado" (no como caída, no cachea). Se asumió así porque la API real no se pudo consultar; confirmar en P1-03.
