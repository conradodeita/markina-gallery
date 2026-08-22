# backend — API PhotoCRM (FastAPI)

Scaffolding da fundação: apenas `GET /health` e um worker placeholder. **Nenhuma funcionalidade de negócio, autenticação, CRUD ou regra do PhotoCRM existe aqui ainda.**

Comandos (Windows; no Linux use `.venv/bin/...`):

- Ambiente: `python -m venv .venv && .venv/Scripts/pip install -r requirements.txt`
- Rodar: `.venv/Scripts/python -m uvicorn app.main:app --port 8000`
- Lint: `.venv/Scripts/python -m ruff check app tests`
- Testes: `.venv/Scripts/python -m pytest -q`
