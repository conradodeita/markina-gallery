# .github/workflows — CI da Markina Gallery

`ci.yml` executa em pull requests (e em pushes na `develop`):

- `backend` — lint (ruff) e testes (pytest)
- `frontend` — lint (eslint), testes (vitest) e build (next build)
- `openspec` — `openspec validate --strict --all`
- `gitleaks` — varredura de segredos no histórico

Segredos de CI ficam exclusivamente no GitHub Secrets.
