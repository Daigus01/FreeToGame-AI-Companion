# PROGRESS — bitácora (añadir entradas nuevas AL FINAL, no reescribir las anteriores)

## 2026-10-27 · Sesión 1 (mañana, 09:57–10:03) — autor: IA anterior
Creó el esqueleto original: `core/`, `db/` (modelos), `migrations/`, `services/` (freetogame, catalog_sync, chat_store), `llm/` (providers, prompts),
`ml/` (ranking, scheduler), `api/` (deps, interactions), tests de orchestrator y ranking, y los archivos base del frontend (`lib/`, configs).
No llegó a escribir `docs/HANDOFF.md` ni `docs/ROADMAP.md` (sus docstrings los referencian). Los IDs `P1-01…P3-06` y `D-02…D-08`, `Q-01` salen de esa sesión.

## 2026-10-27 · Sesión 2 (tarde, ~15:48) — autor: Claude Sonnet 5.5
### Incidente I-01 — sobrescritura accidental
Al empezar creé un esqueleto propio en la misma carpeta sin comprobar que ya había trabajo previo. Sobrescribí archivos que no se pueden restaurar (no había git ni respaldo):
`app/config.py`, `app/llm/orchestrator.py`, `app/llm/tools.py`, `app/ml/pipeline.py`, `tests/test_tools.py` y, posiblemente, `app/main.py` y rutas (`health/games/chat/recommendations`).
Además generé archivos duplicados incompatibles (`app/db.py` vs paquete `app/db/`, `clients/`, `services/cache.py`, `services/catalog.py`, `pyproject.toml`, `db/init/…`, tests propios) que **se eliminaron**.
Reparación (decisión del usuario: "reparar sobre lo anterior"): se adoptó la estructura de la sesión 1 y se reescribieron los módulos perdidos reconstruyendo sus interfaces a partir de lo que importaban/esperaban el resto del código y los tests supervivientes
(`test_orchestrator.py` → contrato de `run_chat` y de `FakeClient`; `scheduler.py` → `run_daily_pipeline(session, client)`; `catalog_sync.py`/`providers.py` → `Settings`, `to_openai_tools`).
Pueden existir diferencias de detalle con las versiones originales (p. ej. recortes de tokens, mensajes de error); la lógica es nueva aunque compatible.
**Lección → regla 1 de CLAUDE.md.**

### Hecho en esta sesión
- Reescritos: `config.py`, `llm/tools.py`, `llm/orchestrator.py`, `ml/pipeline.py`, `api/routes/{health,games,chat,recommendations}.py`, `main.py`, `tests/test_tools.py`.
- Nuevos: `services/recs.py`, `services/users.py`, `get_llm_provider` en `deps.py`, tests `test_freetogame_client.py` y `test_api.py`.
- Infra: `docker-compose.yml` (monta `backend/migrations`), `backend/Dockerfile`, `.env.example`, `Makefile`, `.gitignore`.
- Frontend: `app/layout.tsx`, `app/page.tsx`, `components/{GameCard,Filters,GameModal,Top5Widget,ChatWidget}.tsx`.
- Docs: `CLAUDE.md`, `README.md`, `docs/{HANDOFF,ROADMAP,TRACEABILITY,PROGRESS}.md`, `docs/SRS.md` ya existía (idéntico al SRS recibido).
### Verificación
`python -m pytest -q` → 20 passed. `npm run typecheck` → sin errores. Docker, Redis, Postgres, FreeToGame y LLM reales: **no probados**.
### Siguiente
P1-01 → P1-02 → P1-03 → P1-06 (ver ROADMAP). Preguntas que conviene resolver pronto: Q-01 (auth) y Q-05 (criterio RNF-1).

## 2026-10-27 · Sesión 3 (16:40) — autor: Claude Sonnet 5.5 — rama `p1-01-verify-stack`
Objetivo: P1-01 (arranque real). El sandbox no tiene daemon Docker ni acceso a freetogame.com, así que se verificó el stack equivalente en local:
Postgres 16 + Redis 7 reales, `backend/scripts/fake_freetogame.py` como upstream, backend con uvicorn.
### Verificado ✅
- Migraciones 001+002 → 7 tablas. `/health` → `{"status":"ok","redis":true,"db":true}`. CORS preflight desde :3000 OK.
- Caché: 2 peticiones iguales = 1 llamada upstream; TTL fresca 43200 s, `:stale` 2592000 s.
- Fallback: con upstream caído y clave fresca expirada → 200 con copia stale; sin copia → 503. Filtros inválidos → 422. `/api/filters` OK.
- `catalog_sync` ×2 → 60 filas (idempotente). Interacciones → 201; `/api/library` OK.
- `run_daily_pipeline` ×2 → 1 fila (idempotente), 5 ids; `/api/recommendations/today`: `fallback_popular` antes del batch, `ml` después; juegos jugados/descartados excluidos (RF-3.3).
- `/api/chat` sin clave → 503 claro.
### Bugs encontrados y corregidos
1. `GET /api/games/{id}` con id inexistente devolvía 503: el cliente trataba el HTTP 404 de FreeToGame como caída. Ahora 404 = "no encontrado" (no usa stale, no cachea). Test nuevo.
2. `POST /api/interactions` daba 500 si el juego no estaba en `games` o el usuario no existía. Ahora 404 y creación lazy del usuario dev (P1-05 parcial).
### No verificado
`docker compose up` (sin daemon), API real de FreeToGame (P1-03), frontend en navegador (P1-06), OpenAI (P2-01), scheduler cron real (P3-03).
### Tests
`python -m pytest -q` → 21 passed.
### Siguiente
En máquina con Docker + internet: `docker compose up`, `make sync`/equivalente, abrir http://localhost:3000 (P1-01, P1-03, P1-06). Luego Q-01 → P1-04.

## 2026-10-27 · Sesión 4 (16:33–16:40 hora CDMX) — verificación por el dueño + revisión de merge
Resultados reportados por el dueño (Windows, Docker Desktop), ejecutados sobre `main`:
- `docker compose up` → todo arrancó bien.
- `catalog_sync` con la API real → **419 juegos** en `games` (primer intento falló por ejecutar con el Python de Windows, sin dependencias: se debe usar `docker compose exec backend python -m app.services.catalog_sync`).
- `pytest` en el contenedor → 20 passed (es `main`; la rama `p1-01-verify-stack` tiene 21 con el test del 404).
Revisión de la rama `p1-01-verify-stack` para merge: ver sección "Revisión de merge" más abajo.
### Revisión de merge (rama p1-01-verify-stack → main)
Diff: 9 archivos, +117/-16; código de producción solo en `interactions.py` (+404 y ensure_user) y `services/freetogame.py` (HTTP 404 = no encontrado). 21 tests y `tsc` en verde, sin secretos ni `.env` versionados, `main` no avanzó (merge sin conflictos).
Riesgos conocidos y aceptados: (1) el manejo del 404 asume que FreeToGame responde HTTP 404 para ids inexistentes; si respondiera 200 con `{"status":0}` también funciona (rama ya cubierta por el test original); un 404 en `/games` (lista) devolvería lista vacía en vez de error. (2) la auth sigue siendo el stub `X-User-Id` (no desplegar en público, P1-04).
Confirmación del dueño ya sobre la rama `p1-01-verify-stack` (Docker/Windows): `catalog_sync` → 419 juegos, `pytest` → **21 passed**. Pendiente de confirmar: `GET /api/games/999999` debe dar 404 en la rama (API real).

## 2026-10-27 · Sesión 5 (20:40 hora COL) — merge a main
Confirmaciones del dueño: `GET /api/games/999999` → **404** con la API real (cierra la duda del manejo del 404); catálogo, filtros y modal de detalle funcionan en el navegador (P1-06 parcial).
Rama `p1-01-verify-stack` mergeada a `main` (fast-forward, sin conflictos). Estado base de `main`: 21 tests, `tsc` limpio, Docker verificado por el dueño.
Siguiente: Q-01 (auth) → P1-04; verificar chat/Top 5 en UI (P1-06 resto); programar `catalog_sync` (P1-02); luego Fase 2 (necesita OPENAI_API_KEY).
