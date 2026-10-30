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

## 2026-10-27 · Sesión 6 (20:48) — P1-04 OAuth (Google + Discord) — rama `p1-04-oauth`
Decisión del dueño: Q-01 → OAuth, solo Google y Discord (registrada como D-11).
### Hecho
- Backend: `auth/session.py` (cookies firmadas), `auth/providers.py` (flujo authorization-code con httpx), `api/routes/auth.py`, `services/users.py` (`upsert_oauth_user`), `deps.get_current_user_id` por cookie (header solo con `ALLOW_DEV_AUTH=true`), CORS con credenciales, migración `003_auth.sql` (+`users.name/avatar_url`, tabla `user_identities`), nuevas variables de entorno, `itsdangerous` en requirements.
- Frontend: `AuthButton`, `lib/api.ts` con `credentials: "include"` y `ApiError`, avisos (`?auth_error=`), mensajes 401/503 en chat y modal.
- Docs: `docs/OAUTH_SETUP.md` (guía de credenciales y migración), HANDOFF (D-11, Q-01 resuelta), ROADMAP (P1-04 🟡, nueva P1-11), TRACEABILITY, README, `.env.example`.
### Verificación
- `pytest`: **42 passed** (21 previos + 21 de auth: firma/expiración/forjado de cookies, state CSRF, URLs de autorización, normalización Google/Discord, canje de código con HTTP simulado, rutas login/callback/me/logout, rechazos, dependencia con/sin dev-auth).
- Postgres real: migración 003 sobre BD existente (idempotente); `upsert_oauth_user`: mismo login → mismo usuario, Discord con el mismo correo verificado → se vincula, nombre/avatar se actualizan, correo normalizado a minúsculas, 3 primeros logins simultáneos → un solo usuario.
- Servidor real: sin sesión 401 en `/me` y Top 5; header `X-User-Id` rechazado; cookie falsificada 401; con cookie válida `/me`, interacciones, biblioteca y Top 5 OK; state falso → `?auth_error=state`; CORS con credenciales OK.
- Navegador (Playwright/Chromium): botones Google/Discord sin sesión, aviso de `auth_error` y limpieza de la URL, modal avisa "Inicia sesión…", con sesión se ve el usuario, el Top 5 y "Guardado en tu biblioteca", chat sin clave LLM muestra "no está configurado". Sin errores JS. `tsc` limpio.
### No verificado
Login real con Google/Discord (el sandbox no llega a esos hosts y faltan credenciales) → **P1-11**, a cargo del dueño con `docs/OAUTH_SETUP.md`.
### Notas
- Cambio de comportamiento: `ALLOW_DEV_AUTH` es `false` por defecto, así que sin OAuth configurado Top 5, chat y biblioteca devuelven 401 (el catálogo sigue público). Para desarrollo sin OAuth: `ALLOW_DEV_AUTH=true` + `NEXT_PUBLIC_DEV_USER_ID=<uuid>`.
- El nombre del usuario se actualiza con el del último proveedor usado (puede alternar entre Google y Discord).
- El modal de detalle aún no cierra con ESC (ya listado en P1-08).
- Despliegue: existente BD → aplicar migración 003 a mano (ver OAUTH_SETUP §4).

## 2026-10-28 · Sesión 7 (08:06 hora CDMX) — merge de P1-04
El dueño confirmó que el login (Google y Discord) funciona con credenciales reales → P1-04 y P1-11 ✅. Rama `p1-04-oauth` mergeada a `main` (fast-forward). Siguiente: Fase 2.

## 2026-10-28 · Sesión 8 (13:12 CDMX) — Fase 2 (chatbot) sin LLM real — rama `p2-chatbot`
Contexto: el dueño autorizó el merge de P1-04 y seguir con la siguiente fase. El merge ya estaba hecho en `main` (otra sesión, fast-forward; `p2-chatbot` partía de `main` sin trabajo previo). Sin API key de LLM disponible → se hizo todo lo que no la necesita.
### Hecho
- **P2-03 tarjetas** (`llm/cards.py`, D-12): solo juegos de resultados de herramientas cuyo título exacto menciona el texto. Cambió el contrato de `test_orchestrator` (antes: hasta 6 tarjetas con todos los resultados).
- **P2-02 prompt** reescrito (vocabulario de categorías, `sort_by`, una categoría por consulta, seguimiento sin re-consultar, títulos exactos) + **20 casos** y harness `evals/chat_eval.py` (aciertos de herramienta/argumentos, p50/p95 de latencias vs RNF-1, `--verbose`, `--out`).
- **P2-05** recorte de historial por tamaño (`llm/history.py`, D-13); caché Redis descartada con justificación.
- **P2-06** `GET /api/chat/sessions` y `/{id}/messages` (+ `services/chat_view.py`), restauración en UI.
- **P2-07** `AnthropicProvider` (D-15) + `LLM_PROVIDER=mock` (D-14).
- **P2-08 (parcial)** botón Parar, Nueva conversación, scroll automático.
- **P2-04** `tests/test_chat_integration.py` (Postgres real) + prueba en navegador.
### Verificación
- `pytest`: **68 passed** (42 previos + 26 nuevos: cards/history, providers, chat_view, eval harness y 2 de integración). Los 2 de integración corren con Postgres real y se omiten sin BD (comprobado).
- Navegador (Playwright) con `LLM_PROVIDER=mock`: enviar → 3 tarjetas correctas → clic abre el modal → recargar restaura mensajes y tarjetas → Nueva conversación vacía → la nueva conversación es la restaurada tras recargar. Sin errores JS. `tsc` limpio.
- `python -m evals.chat_eval --provider mock --offline` → 14/20 (esperado: el mock no sabe no usar herramientas, pedir detalles, ordenar alfabéticamente ni "battle-royale"); confirma que el harness discrimina.
### No verificado (necesita clave real)
OpenAI/Anthropic en vivo (streaming de `tool_calls`, calidad del prompt, seguimiento "¿y de esos…?"), latencias RNF-1 → **P2-01/P2-02/P2-07**, a cargo del dueño: ver HANDOFF §8.
### Notas
- `get_games_by_filter` solo acepta una categoría; "MMORPG de fantasía" depende de que el LLM filtre (nueva P2-09: endpoint `/filter?tag=`, por verificar contra la API real).
- Títulos con puntuación o muy cortos pueden dar falsos positivos/negativos en las tarjetas; se observará con el LLM real.
- Siguiente: correr `chat_eval` con una clave (P2-01/02) → iterar prompt → Fase 3 (P3-01 extracción de preferencias, que sí necesita LLM).

## 2026-10-28 · Sesión 8b (14:10 CDMX) — recomendaciones en el catálogo (D-16) — rama `p2-chatbot`
El dueño confirmó que Fase 2 funciona con `mock` y con la API real de Anthropic, y pidió que los juegos recomendados se rendericen **en el catálogo, no en el chat**.
### Hecho (solo frontend; backend y contrato SSE intactos)
- `app/page.tsx`: estado `recs`; la cuadrícula muestra las recomendaciones con banner «Recomendados por el asistente · N» y «Ver todo el catálogo»; cambiar un filtro sale del modo; scroll del catálogo a la vista al recomendar.
- `ChatWidget.tsx`: ya no dibuja tarjetas; enlace «↗ Ver N juegos recomendados en el catálogo» por mensaje (también en conversaciones restauradas); prop `onRecommend`.
- **Bug corregido (mío, de P2-08):** el autoscroll del chat usaba `scrollIntoView`, que también movía la página y, en móvil (chat bajo el catálogo), anulaba el scroll hacia las recomendaciones. Ahora solo desplaza el contenedor del chat.
### Verificación
Navegador (Playwright, `LLM_PROVIDER=mock`, Postgres real), 16 comprobaciones: catálogo normal al inicio; tras preguntar el catálogo muestra exactamente los 3 juegos nombrados en la respuesta; el chat no tiene tarjetas; enlace del chat; clic en recomendado abre modal; «Ver todo el catálogo»; filtro sale del modo; 2.ª consulta reemplaza; recarga → catálogo normal + enlaces restaurados que reaplican las recomendaciones (hidratadas); móvil 390 px: el catálogo queda a 16 px del borde superior; sin errores JS. `tsc` limpio. Backend sin cambios (68 tests).
### Decisiones de diseño a revisar por el dueño
(1) Al recargar NO se auto-aplican recomendaciones viejas (se reaplican con el enlace del chat). (2) Una recomendación nueva reemplaza la cuadrícula completa (los filtros no se combinan con ella). (3) Se aparta de SRS RF-2.3: documentado en D-16.

## 2026-10-30 · Sesión 9 — validación con LLM real y merge a `main`
El dueño pegó la salida de `python -m evals.chat_eval` con LLM real, confirmó que las recomendaciones en el catálogo (D-16) funcionan y autorizó el merge de `p2-chatbot` a `main`.
### Resultados de la evaluación (P2-01 / P2-02 / P2-07)
- **Aciertos: 20/20 (100 %)**, objetivo ≥ 90 %. Herramienta y argumentos correctos en todos los casos (p. ej. `mmorpg`+`pc`+`release-date`, `pvp`+`pc`+`alphabetical`, `battle-royale`, `sci-fi`); `details-of-first` usa `get_game_details`; seguimiento, saludo y fuera de tema no llaman herramientas; consulta en inglés respondida en inglés.
- **Latencias vs RNF-1:** primer token p50 **2.96 s** / p95 5.36 s (**no cumple < 1.5 s**); primer evento visible (tool_call o token) p50 **1.12 s** / p95 2.19 s; ejecución de herramienta p50 **0.42 s** / p95 0.62 s (cumple < 3 s). El primer token incluye la ida y vuelta al LLM tras la herramienta.
### Observaciones
- Respuestas con títulos del catálogo (sin inventados en lo muestreado). Algunos textos pierden espacios («lafranquicia», «veteranoy», «decarreras») al cortarse el extracto de la salida; **por verificar si es el recorte del reporte o un artefacto de los deltas de streaming** (revisar con `--verbose`/UI antes de cerrar P2-08).
- `racing-browser` recomendó Transformice (no es de carreras) admitiéndolo: aceptable, pero el catálogo para esa combinación es de solo 2 juegos.
### Decisiones / pendientes
- P2-10/Q-05: proponer medir RNF-1 como «primer evento visible» (1.12 s cumple); el dueño debe decidirlo.
- OpenAI en vivo sigue sin probarse (solo si se va a usar).
- Siguiente: Fase 3 (P3-01 extracción de preferencias desde el chat).

## 2026-10-30 · Sesión 10 — README ampliado y cierre de Q-05 — rama `p3-docs-readme`
- **Q-05 resuelta por el dueño:** RNF-1 se mide como «primer evento visible» (cumple: p50 1.12 s). P2-10 ✅.
- **README.md** reescrito: arquitectura, dónde vive la base de datos (volumen Docker `pgdata`, tablas, Redis solo caché), prueba rápida paso a paso (incluye Windows sin `make`), qué probar en la UI, tests/evals, operaciones útiles y explicación del algoritmo de recomendación.
- Sin cambios de código.
