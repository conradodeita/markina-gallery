# Validação

- `npx --yes @fission-ai/openspec@1.14.0 validate clarify-order-delivery-access-hint --strict --no-interactive` — passou; change válida.
- `npm exec vitest run app/library/order-delivery.test.tsx` em `frontend/` — passou; 1 arquivo e 5 testes.
- `npm exec eslint app/library/purchase-card.tsx app/library/order-delivery.test.tsx` em `frontend/` — passou.
- `npm exec tsc -- --noEmit` em `frontend/` — passou.
- `npm run build` em `frontend/` — passou; compilação, verificação TypeScript e geração das páginas concluídas.
- `git diff --check` — passou sem erros de whitespace.
