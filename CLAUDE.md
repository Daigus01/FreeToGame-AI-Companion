# FreeToGame AI Companion — instrucciones para cualquier IA/humano que retome el proyecto

**Lee en este orden:** `docs/HANDOFF.md` → `docs/ROADMAP.md` → `docs/PROGRESS.md` (último registro).
Fuente de verdad de requisitos: `docs/SRS.md`. Trazabilidad requisito→código: `docs/TRACEABILITY.md`.

## Comandos
- `make test` — tests backend (deben estar en verde antes y después de cada cambio).
- `make typecheck` — tsc del frontend.
- `make todo` — lista todos los `TODO(Px-yy)`; cada ID está definido en `docs/ROADMAP.md`.
- `make eval` — evalúa el chatbot (`backend/evals`); necesita API key salvo `ARGS="--provider mock --offline"`.
- `make up` — docker compose (Postgres, Redis, backend, frontend). `make sync` — rellena tabla `games`.

## Reglas de trabajo
1. Antes de crear/editar un archivo, comprueba si ya existe (`ls`, `git status`). **No sobrescribas trabajo previo** (ver incidente I-01 en PROGRESS.md).
2. Cada módulo lleva en su docstring `STATUS:` (done / stub / untested) y `TODO(Px-yy)`. Mantenlo al día.
3. Al cerrar una tarea: actualiza ROADMAP.md (estado), añade entrada en PROGRESS.md, ajusta TRACEABILITY.md si cambia un requisito.
4. Decisiones nuevas → `docs/HANDOFF.md` sección Decisiones (D-xx). Preguntas abiertas → sección Q-xx.
5. Secretos solo en backend `.env` (RNF-4). Nunca `NEXT_PUBLIC_*` para claves.
6. Contratos que no se rompen sin actualizar ambos lados: eventos SSE del chat (HANDOFF §6), `backend/app/schemas.py` ↔ `frontend/lib/types.ts`, `backend/app/schemas.py CATEGORIES` ↔ `frontend/lib/constants.ts`.
