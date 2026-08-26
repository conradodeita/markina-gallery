# backend — API Markina Gallery (FastAPI)

Inclui autenticação unificada com OTP sandbox do cliente e senha + TOTP do administrador. O cookie de sessão é opaco, `HttpOnly`, `Secure` fora de desenvolvimento e `SameSite=Lax`; `/admin` e `/gallery/{id}` são autorizados no servidor.

Comandos (Windows; no Linux use `.venv/bin/...`):

- Ambiente: `python -m venv .venv && .venv/Scripts/pip install -r requirements.txt`
- Rodar: `.venv/Scripts/python -m uvicorn app.main:app --port 8000`
- Lint: `.venv/Scripts/python -m ruff check app tests`
- Testes: `.venv/Scripts/python -m pytest -q`
