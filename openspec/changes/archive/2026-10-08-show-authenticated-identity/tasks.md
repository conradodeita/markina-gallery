## 1. Identidade autenticada

- [x] 1.1 Criar endpoint autenticado que retorna somente a identidade da sessão atual. Evidência de implementação: `GET /auth/identity` valida `current_session`, busca e-mail da conta admin ou telefone ativo/verificado da cliente autenticada e não recebe sujeito por parâmetro.
- [x] 1.2 Exibir e-mail do fotógrafo e telefone da cliente nos cabeçalhos autenticados compartilhados. Evidência de implementação: `AuthenticatedIdentity` consulta o endpoint sem cache e é incluído nos layouts `/admin`, `/library` e `/gallery`.
- [x] 1.3 Validar o contrato e a apresentação e registrar evidências. Backend: `python -m pytest -q tests/test_auth.py -k authenticated_identity` aprovou 2 testes em SQLite temporário isolado. Frontend: `npm exec vitest -- run app/authenticated-identity.test.tsx` aprovou 3 testes. `python -m ruff check app/main.py tests/test_auth.py`, ESLint focal, `npm exec tsc -- --noEmit`, `npm run build` e `git diff --check` passaram.
- [x] 1.4 Validar a change no OpenSpec. Evidência: `npx --yes @fission-ai/openspec validate show-authenticated-identity --strict --no-interactive` retornou `Change 'show-authenticated-identity' is valid`.

## Continuidade

- Implementação, validações locais, sincronização da spec principal e arquivamento concluídos em 2026-10-08, após autorização humana.
