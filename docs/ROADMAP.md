# Roadmap

Leyenda: ✅ hecho y probado · 🟡 implementado sin verificar en vivo · ⬜ pendiente · ❓ bloqueado por pregunta (Q-xx en HANDOFF.md)
Cada ID aparece como `TODO(ID)` en el código (`make todo`). Orden sugerido: P1 → P2 → P3 → P4; dentro de una fase, por ID.
Última actualización: 2026-10-27, sesión 3 (ver PROGRESS.md).

## Fase 0 — Cimientos ✅
Estructura, SRS en docs, esquema SQL (migrations/001+002), modelos SQLAlchemy, config, cliente FreeToGame con caché 12 h + fallback stale,
herramientas LLM (SRS §5), orquestador con tool-calling, proveedor OpenAI, lógica de ranking/diversidad, scheduler 00:00 UTC, frontend base, docker-compose.
Verificado: `make test` (20 tests) y `make typecheck`. **No verificado:** nada contra Postgres/Redis/FreeToGame/OpenAI reales.

## Fase 1 — MVP Catálogo + API (SRS Fase 1; RF-1.x, RNF-2/3)
| ID | Tarea | Estado | Criterio de aceptación |
|---|---|---|---|
| P1-01 | Levantar `docker compose up`; comprobar migraciones y caché Redis reales | ✅ `docker compose up` ejecutado por el dueño en Windows (todo arrancó bien); además verificado con Postgres/Redis reales en el sandbox | `/health` = ok; 2ª petición a `/api/games` no sale a internet; TTL 12 h visible con `redis-cli ttl` |
| P1-02 | Ejecutar `catalog_sync` y programarlo a diario antes del batch ML (p.ej. 23:30 UTC) | 🟡 `catalog_sync` verificado con la API real: 419 juegos en `games` (Windows/Docker) e idempotente; **falta programarlo a diario** | tabla `games` ≈ catálogo completo; re-ejecución idempotente |
| P1-03 | Verificar `FreeToGameClient` contra la API real (campos, `sort-by`, categoría, id inexistente, rate limit) | 🟡 verificado con la API real: lista (419 juegos) e id inexistente (HTTP 404 confirmado → `/api/games/999999` da 404). **Falta:** revisar `sort-by`/categorías con datos reales y rate limit | test de contrato opcional (`pytest -m live`) pasa |
| P1-04 | Auth real: OAuth Google + Discord (D-11) | ✅ verificado por el dueño con login real (2026-10-28) | usuario entra con Google/Discord; endpoints protegidos; cookie no falsificable; header `X-User-Id` rechazado salvo `ALLOW_DEV_AUTH=true` |
| P1-11 | Crear credenciales OAuth (Google, Discord) según `docs/OAUTH_SETUP.md`, aplicar migración 003 y probar login real | ✅ (dueño, 2026-10-28) | login real con ambos proveedores; mismo correo → mismo usuario; `/api/auth/me` OK |
| P1-05 | Interacciones: semántica estado vs evento ❓Q-04, 404/409 si `game_id` no existe, crear usuario si no existe | 🟡 404 y creación de usuario hechos; **semántica pendiente** | guardar→quitar funciona; "jugado" excluye del Top 5 |
| P1-06 | Verificar `frontend/lib/api.ts` ↔ backend E2E; generar tipos desde `/openapi.json` | 🟡 catálogo, filtros y modal verificados a ojo por el dueño en el navegador; **faltan** chat/Top 5 en UI y generar tipos | catálogo carga en el navegador con filtros |
| P1-07 | Pulido catálogo: paginación/skeletons, banner de modo degradado (RNF-3) | ⬜ | UI usable con 400+ juegos; banner si `/health` degraded |
| P1-08 | Modal de detalle: carrusel, foco/ESC, botones de biblioteca conectados | 🟡 | RF-1.3 y RF-1.4 completos en UI |
| P1-09 | Paginación/limit en `/api/games` | ⬜ | `?limit&offset` + frontend |
| P1-10 | Tests de integración con Postgres/Redis reales + CI | ⬜ | pipeline CI verde |
**Hito Fase 1:** un usuario navega, filtra, abre detalle y guarda juegos; la app sigue sirviendo catálogo con la API externa caída.

## Fase 2 — Chatbot LLM + Tool Calling (RF-2.x, RNF-1)
| ID | Tarea | Estado | Criterio |
|---|---|---|---|
| P2-01 | Verificar `OpenAIProvider` en vivo (deltas de tool_calls, streaming); medir RNF-1 (1er token < 1.5 s, tool < 3 s) ❓Q-05 | 🟡 código listo + harness de medición (`python -m evals.chat_eval`); **falta correrlo con una `OPENAI_API_KEY` real (dueño)** | métricas p50/p95 pegadas en PROGRESS.md |
| P2-02 | Afinar `prompts.py` + set de ~20 consultas de evaluación (incluye seguimiento "¿y de esos, el más reciente?") | 🟡 prompt reescrito (vocabulario de categorías, sort_by, una categoría por consulta, títulos exactos) + 20 casos en `backend/evals/cases.py`; **falta validar con un LLM real y iterar** | ≥90 % pasa (`chat_eval`), 0 juegos inventados (revisar respuestas con `--verbose`) |
| P2-03 | Tarjetas = solo juegos realmente recomendados | ✅ tarjeta = juego de un resultado de herramienta cuyo título exacto aparece en el texto (D-12); tests + navegador | tarjetas coinciden con el texto |
| P2-04 | Test E2E del endpoint SSE con proveedor falso + BD real | ✅ `tests/test_chat_integration.py` (Postgres real, se omite si no hay BD) + navegador con `LLM_PROVIDER=mock` | orden de eventos y persistencia verificados |
| P2-05 | Recorte de historial por tamaño; caché Redis del historial | ✅ recorte (`llm/history.py`, D-13). Caché Redis **descartada por ahora** (lectura indexada de ≤30 filas; reabrir si se mide lento) | historial acotado, nunca empieza en un mensaje huérfano |
| P2-06 | `GET /api/chat/sessions` y `GET /api/chat/{id}/messages` + restaurar conversación en UI (RF-2.4) | ✅ verificado en navegador: recargar restaura la última conversación y sus tarjetas; aislamiento entre usuarios (404) | recargar la página conserva el chat |
| P2-07 | `AnthropicProvider` (traducir mensajes formato OpenAI, `to_anthropic_tools`) | 🟡 implementado; traducción y streaming probados con SDK simulado; **falta probar con `ANTHROPIC_API_KEY` real** y correr el mismo `chat_eval` | misma suite de P2-02 pasa con ambos |
| P2-08 | UI chat: markdown, botón parar, reintentar, límite de uso por usuario | 🟡 hecho: parar, nueva conversación, scroll automático. **Faltan:** markdown, reintentar, límite de uso (P4-02) | — |
| P2-09 | Consultas con varias categorías usando el endpoint `/filter?tag=a.b.c` de FreeToGame (hoy `get_games_by_filter` admite una sola; el prompt lo compensa filtrando) | ⬜ (verificar el endpoint con la API real) | "MMORPG de fantasía" devuelve la intersección sin que el LLM filtre |
| P2-10 | Afinar el criterio de RNF-1 con las mediciones reales de P2-01 ❓Q-05 | ⬜ | criterio acordado y reflejado en el SRS/Roadmap |
**Hito Fase 2:** "Busco un MMORPG de fantasía para PC que no sea muy antiguo" → tarjetas reales en el chat, con seguimiento contextual.

## Fase 3 — ML y Top 5 diario (RF-3.x)
| ID | Tarea | Estado | Criterio |
|---|---|---|---|
| P3-01 | Extraer preferencias del chat con el LLM → escribir `user_preference_profiles` (RF-3.2). `ranking.build_profile` ya las lee | ⬜ | tras chatear, el perfil cambia y el Top 5 lo refleja |
| P3-02 | Registro de eventos `view/click` desde UI sin ruido (dedupe/debounce) | 🟡 | `click` se registra al abrir detalle; `view` pendiente |
| P3-03 | Probar `run_daily_pipeline` + scheduler contra Postgres; comando manual de ejecución; idempotencia | 🟡 pipeline verificado con Postgres real (1 fila/usuario/día, 5 ids, idempotente, exclusiones OK); **faltan scheduler real y comando manual** | 1 fila por usuario/día, 5 ids, reglas RF-3.3 |
| P3-04 | Verificar `/api/recommendations/today` y el widget E2E | 🟡 endpoint verificado (`fallback_popular` → `ml` tras el batch); **falta el widget en navegador** | `source=ml` tras el batch, `fallback_popular` antes |
| P3-05 | Evaluación offline (leave-one-out, hit-rate@5) vs línea base de popularidad | ⬜ | informe en docs/ |
| P3-06 | Modelo mejorado (`implicit` ALS / LightGBM) y consultas por lotes (hoy N+1) | ⬜ | supera la línea base en P3-05 |
| P3-07 | Decidir "subgénero" (Q-02) y aplicar en la regla de diversidad | ❓ | regla RF-3.3 documentada |
**Hito Fase 3:** a las 00:00 UTC cada usuario recibe 5 juegos diversos, sin jugados/descartados.

## Fase 4 — Endurecimiento (RNF-3, RNF-4; fuera del SRS original)
P4-01 logging/métricas · P4-02 rate limiting (incluye `/api/auth/*`) · P4-03 despliegue (Vercel + contenedor backend) · P4-04 plan de disponibilidad 99.5 % · P4-05 revisión de seguridad (secretos, CORS, inyección vía datos de tools).
