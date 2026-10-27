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
