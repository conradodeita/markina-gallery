# backend — API Markina Gallery (FastAPI)

Inclui autenticação unificada com OTP sandbox do cliente e senha + TOTP do administrador. O cookie de sessão é opaco, `HttpOnly`, `Secure` fora de desenvolvimento e `SameSite=Lax`; `/admin` e `/gallery/{id}` são autorizados no servidor.

A recuperação administrativa usa OTP no WhatsApp do fotógrafo e link de uso único no e-mail verificado. Configuração, limites, SMTP/DNS, retenção, diagnóstico e rollback estão em `../docs/OPERACAO-RECUPERACAO-CONTA-ADMIN.md`.

O segredo TOTP administrativo é cifrado em repouso e depende de keyring externo dedicado. Provisionamento, rotação, restore e gates de compatibilidade estão em `../docs/OPERACAO-SEGREDO-TOTP.md`.

Antes de iniciar a API com PostgreSQL local, identifique a revisão de destino com `alembic heads` e aplique-a explicitamente com `alembic upgrade <revisão-validada>` em banco descartável ou no ambiente autorizado. Para conferir sem escrita, execute `python -m app.schema_revision_check`. O Compose não aplica migration ao iniciar API/workers; `docker compose -p markina-gallery -f docker/docker-compose.yml run --rm --no-deps migrate` faz somente a conferência. Em produção, siga o faseamento e as autorizações de release, especialmente para `0091`/`0093`; não execute `upgrade head` por inferência. A criação do administrador é deliberada e idempotente: defina `ADMIN_SEED_EMAIL`, `ADMIN_SEED_PASSWORD` (12+ caracteres) e `ADMIN_SEED_TOTP_SECRET` somente no arquivo de ambiente externo, então execute `python -m app.seed_admin`. O comando nunca imprime nem sobrescreve segredos.

Comandos (Windows; no Linux use `.venv/bin/...`):

- Ambiente: `python -m venv .venv && .venv/Scripts/pip install -r requirements.txt`
- Rodar: `.venv/Scripts/python -m uvicorn app.main:app --port 8000`
- Lint: `.venv/Scripts/python -m ruff check app tests`
- Testes: `.venv/Scripts/python -m pytest -q`
