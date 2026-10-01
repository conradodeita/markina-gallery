# .github/workflows — CI da Markina Gallery

`ci.yml` executa em pull requests (e em pushes na `develop`):

- `backend` — lint (ruff) e testes (pytest)
- `frontend` — lint (eslint), testes (vitest) e build (next build)
- `openspec` — `openspec validate --strict --all`
- `gitleaks` — varredura de segredos no histórico

Segredos de CI ficam exclusivamente no GitHub Secrets.

O job backend fornece dois PostgreSQL sintéticos separados: a fundação histórica
em 55469 e a integração de fotógrafos em 15470. `PHOTOGRAPHER_TEST_DATABASE_URL`
habilita os ensaios de constraints, migration, autorização, leases e isolamento A/B
em bancos/schemas UUID descartáveis; credenciais desses serviços existem somente
no runner de testes. Não configuram infraestrutura ou canais de homologação.
O ensaio visual 2 × 3 é opt-in (`PYP_RUN_LOCAL_PILOT=1`), requer build Next e
Edge/Playwright e possui evidência local registrada no OpenSpec.
