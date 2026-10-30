# FreeToGame AI Companion & Recommendation Platform

Portal de videojuegos Free-to-Play con tres piezas:

1. **Catálogo** alimentado por la API pública de [FreeToGame](https://www.freetogame.com/api-doc) (filtros, detalle, biblioteca personal).
2. **Chatbot con LLM y tool calling**: consulta el catálogo en vivo según lo que pida el usuario; los juegos que recomienda se muestran en el catálogo (D-16).
3. **Top 5 diario** por usuario, calculado por un motor de recomendación a partir de su historial.

Requisitos: `docs/SRS.md` · Estado y próximos pasos: `docs/ROADMAP.md` · Guía para retomar el trabajo: `CLAUDE.md` y `docs/HANDOFF.md`.

## Arquitectura

```
Navegador ── Next.js (:3000) ──HTTP/SSE──▶ FastAPI (:8000) ──▶ FreeToGame API (con caché)
                                              │      │
                                              │      └──▶ Redis (caché de la API, 12 h + copia "stale" 30 d)
                                              └─────────▶ PostgreSQL (usuarios, biblioteca, chat, Top 5)
                                              └─────────▶ LLM (OpenAI / Anthropic / mock)
```

```
frontend/   Next.js 15 + React 19 + Tailwind (app/, components/, lib/)
backend/    FastAPI async (app/api, app/llm, app/ml, app/services, app/db, app/core)
  migrations/  SQL canónico: 001 esquema base, 002 preferencias, 003 auth OAuth
  tests/       pytest (unitarios + 2 de integración que se omiten sin BD)
  evals/       evaluación del chatbot contra un LLM real
docs/       SRS, HANDOFF, ROADMAP, PROGRESS, TRACEABILITY, OAUTH_SETUP
```

## Dónde vive la base de datos

- **PostgreSQL 16** en el contenedor `postgres` de `docker-compose.yml`. Datos persistentes en el volumen Docker **`pgdata`** (sobrevive a `docker compose down`; se borra con `docker compose down -v`).
- Credenciales de desarrollo: usuario `ftg`, contraseña `ftg`, base `ftg`, puerto `5432` publicado en tu máquina: `postgresql://ftg:ftg@localhost:5432/ftg`.
- El esquema se crea solo **la primera vez** que se inicializa el volumen: Docker ejecuta `backend/migrations/*.sql` en orden. Si añades una migración nueva con un volumen ya creado, aplícala a mano (ver «Operaciones útiles»).
- Tablas: `users`, `user_identities` (Google/Discord), `games` (copia local del catálogo), `user_game_interactions` (view/click/saved/played/disliked), `chat_sessions`, `chat_messages`, `daily_recommendations` (un Top 5 por usuario y día), `user_preference_profiles`.
- **Redis 7** (contenedor `redis`) guarda solo caché de las respuestas de FreeToGame; no es fuente de verdad.
- La API de FreeToGame no se guarda como base propia: el catálogo se lee de ella (con caché) y `make sync` deja una copia en `games`, necesaria para registrar interacciones.

## Prueba rápida (≈ 5 minutos)

**Requisitos:** Docker Desktop (Windows/macOS/Linux) y Git. No necesitas Python ni Node locales.

```bash
git clone https://github.com/Daigus01/FreeToGame-AI-Companion.git
cd FreeToGame-AI-Companion
cp .env.example .env            # Windows PowerShell: Copy-Item .env.example .env
```

Edita `.env` según lo que quieras probar:

| Quiero probar… | Qué poner en `.env` |
|---|---|
| Solo catálogo y filtros | nada (los valores por defecto sirven) |
| Chat **sin** clave (demo) | `LLM_PROVIDER=mock` |
| Chat con Anthropic | `LLM_PROVIDER=anthropic` y `ANTHROPIC_API_KEY=...` |
| Chat con OpenAI | `LLM_PROVIDER=openai` y `OPENAI_API_KEY=...` |
| Iniciar sesión (Top 5, biblioteca, historial del chat) | credenciales OAuth: ver `docs/OAUTH_SETUP.md` |

```bash
docker compose up --build       # Postgres + Redis + backend (:8000) + frontend (:3000)
# en otra terminal, cuando el backend esté arriba:
docker compose exec backend python -m app.services.catalog_sync     # rellena `games` (~419 juegos)
```

Abre **http://localhost:3000**. Comprobaciones: `http://localhost:8000/health` y la documentación interactiva en `http://localhost:8000/docs`.

> **Sin `make` (Windows):** usa los comandos `docker compose ...` de arriba; el `Makefile` es solo un atajo (`make up`, `make sync`, `make test`).

### Qué probar en la interfaz

1. **Catálogo:** filtra por plataforma, categoría y orden; abre un juego para ver su detalle.
2. **Chat:** escribe «un MMORPG de fantasía para PC, de los más recientes». Verás el aviso «Consultando catálogo…», la respuesta en streaming y el catálogo mostrando solo los juegos recomendados (botón «Ver todo el catálogo» para volver). Prueba un seguimiento: «¿y de esos, el más reciente?» (no vuelve a consultar).
3. **Con sesión iniciada:** marca juegos como guardado / jugado / no me interesa; mira el widget **Top 5** y la biblioteca.

### Tests y evaluación

```bash
docker compose exec backend python -m pytest -q                    # 68 tests (2 de integración usan la BD real)
docker compose exec backend python -m evals.chat_eval --verbose    # 20 consultas contra el LLM real (necesita clave)
docker compose exec backend python -m evals.chat_eval --provider mock --offline   # autotest del harness (~14/20 esperado)
```

Sin Docker (Linux/macOS con Python 3.11+): `make test` instala dependencias y ejecuta los tests unitarios.

### Operaciones útiles

```bash
docker compose logs -f backend                                  # logs del backend
docker compose exec postgres psql -U ftg -d ftg                 # consola SQL
docker compose exec postgres psql -U ftg -d ftg -c "select count(*) from games;"
docker compose exec -T postgres psql -U ftg -d ftg < backend/migrations/00X_nueva.sql   # aplicar migración nueva
docker compose down            # parar (conserva datos)
docker compose down -v         # parar y BORRAR la base de datos
```

### Desarrollo sin acceso a FreeToGame
`python backend/scripts/fake_freetogame.py 9000` y `FREETOGAME_BASE_URL=http://localhost:9000/api` en `.env`. Ver `docs/HANDOFF.md` §8.

## Cómo recomienda el sistema (Top 5 diario)

Motor **basado en contenido con retroalimentación implícita** (código puro y testeable en `backend/app/ml/ranking.py`; no es aún un modelo entrenado):

1. **Perfil del usuario.** Cada interacción suma o resta afinidad al *género* y a la *plataforma* del juego: `view` +1, `click` +2, `saved` +5, `played` +1, `disliked` −4. Las preferencias detectadas en el chat (cuando se implemente P3-01) pesan como un «guardado» para el género y +3 para la plataforma.
2. **Puntuación de cada juego candidato:** `afinidad_de_género + 0.5 × afinidad_de_plataforma + prior_de_popularidad`, donde el prior va de 0 a 1 según el ranking de popularidad de FreeToGame (el juego más popular suma 1). Para un usuario nuevo, la afinidad es 0 y manda la popularidad (arranque en frío).
3. **Exclusiones:** se descartan los juegos marcados como *jugado* o *no me interesa*.
4. **Diversidad:** selección voraz en orden de puntuación con **máximo 2 juegos por género** (la API no ofrece subgéneros, D-07); si el tope deja menos de 5, se rellena con los saltados.
5. **Ejecución:** un job (APScheduler, 00:00 UTC) calcula el Top 5 de todos los usuarios y lo guarda en `daily_recommendations` (idempotente por usuario y día). `GET /api/recommendations/today` devuelve la fila guardada o, si aún no existe, calcula lo mismo al vuelo.

Limitaciones conocidas: no hay filtrado colaborativo ni modelo entrenado (ver roadmap P3-06 para `implicit`/LightGBM cuando haya datos de interacción suficientes); el género es la única señal de contenido.
