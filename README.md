# FreeToGame AI Companion & Recommendation Platform

Portal F2P con catálogo (API FreeToGame), chatbot LLM con tool calling y Top 5 diario por ML.
Requisitos: `docs/SRS.md`. Estado y siguientes pasos: `docs/ROADMAP.md`. Guía para retomar: `CLAUDE.md`.

```
frontend/   Next.js 15 + Tailwind (app/, components/, lib/)
backend/    FastAPI (app/api, app/llm, app/ml, app/services, app/db, app/core) + tests/
  migrations/  SQL canónico (001 = SRS §6, 002 = extensión preferencias)
docs/       SRS, HANDOFF, ROADMAP, PROGRESS, TRACEABILITY
```

## Arranque rápido
```bash
cp .env.example .env        # añade OPENAI_API_KEY para el chat
make up                     # Postgres+Redis+backend(:8000)+frontend(:3000)
make sync                   # (otra terminal) rellena `games`
make test                   # tests backend sin servicios externos
```
Sin API key el catálogo funciona; `/api/chat` responde 503. La auth es un stub de desarrollo (`X-User-Id`).

## Desarrollo sin acceso a FreeToGame
`python backend/scripts/fake_freetogame.py 9000` y `FREETOGAME_BASE_URL=http://localhost:9000/api` en `.env`. Ver `docs/HANDOFF.md` §8.
