.PHONY: up down test sync todo typecheck eval
up: ; docker compose up --build
down: ; docker compose down
test: ; cd backend && pip install -r requirements.txt --break-system-packages -q && python -m pytest -q
sync: ; cd backend && python -m app.services.catalog_sync     # fills `games` (needed before interactions, P1-02)
eval: ; cd backend && python -m evals.chat_eval $(ARGS)
typecheck: ; cd frontend && npm install && npm run typecheck
todo: ; @grep -rn "TODO(P" backend/app frontend/app frontend/components frontend/lib db docs 2>/dev/null | sort -t'(' -k2
