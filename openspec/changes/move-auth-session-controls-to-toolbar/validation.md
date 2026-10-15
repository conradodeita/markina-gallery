# Validação

- `npm exec vitest run app/admin-session-toolbar.test.tsx` em `frontend/` — passou; 1 arquivo e 3 testes.
- `npm exec eslint app/admin-session-toolbar.tsx app/admin-session-toolbar.test.tsx app/layout.tsx app/admin/layout.tsx` em `frontend/` — passou.
- `npm exec tsc -- --noEmit` em `frontend/` — passou.
- `npm run build` em `frontend/` — passou; compilação, verificação TypeScript e geração das páginas concluídas.
- `npx --yes @fission-ai/openspec@1.14.0 validate move-auth-session-controls-to-toolbar --strict --no-interactive` — passou; change válida.
- `git diff --check` — passou sem erros de whitespace.
