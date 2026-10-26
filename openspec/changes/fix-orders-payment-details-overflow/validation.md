# Validação — 26/10/2026

- Defeito observado na sessão autorizada do Chrome em `/admin/payments`: ID de order invade a célula de estado e ID de transação ultrapassa o card.
- Branch `codex/fix-orders-payment-details-overflow`, base `52b9886b` da main. O outro chat confirmou escopo independente `expand-preview-adjustment-strength-range` (prévia e migration 0090); nenhum arquivo funcional em comum. Nenhum deploy concorrente iniciado por esta change.
- Ensaio local em Edge headless com HTML sintético equivalente ao trecho afetado e os CSS reais global/module. O CSS original reproduziu overflow desktop; o corrigido passou em 390, 768, 1024 e 1686 px, temas claro/escuro: oito combinações sem overflow dos valores/documento, quatro linhas distintas e identificadores integrais preservados. Captura desktop escura inspecionada. Este ensaio valida geometria isolada, não a página autenticada após publicação.
- Script, relatório e capturas locais ignorados em `.codex-tmp/orders-overflow-qa*`, sem dados pessoais ou chamadas ao provedor.
- `npx tsc --noEmit` e ESLint da página passaram sem erros.
- `npm run build` passou: compilação, TypeScript e geração das 23 páginas estáticas concluídos.
- OpenSpec estrito e `git diff --check` passaram.
- Revisão proporcional: alteração limitada ao CSS de fatos dentro de paymentSection; sem mudança de dados, lógica financeira, PIX, backend, API, migrations, credenciais ou regras entre tenants. CSS global continua consumido pelos metadados gerais e não foi removido.

## Seguimento — Mais filtros no mesmo PR #295

- Proprietário autorizou incluir a sobreposição Situação financeira/Provedor no mesmo envio. Defeito confirmado visualmente no Chrome em 1265 px; outro chat avisado da atualização de escopo e do novo push.
- Três regras adicionais no mesmo CSS Module: grade auto-fit com mínimo útil de 240 px limitado a 100% da largura disponível; itens podem encolher; selects/datas usam largura da célula com box-sizing border-box. Nenhuma opção ou handler alterado.
- Ensaio sintético com os CSS reais reproduziu overflow anterior em 1265 px. Corrigido sem overflow em 320, 390, 768, 1024, 1265 e 1686 px, temas claro/escuro (12 combinações), com as quatro opções de provedor preservadas. Captura desktop inspecionada; geometria isolada não substitui validação autenticada pós-publicação. Os oito casos anteriores de IDs também foram repetidos e passaram.
- `npm test -- app/admin/payments/redesign.test.tsx app/admin/payments/page.test.tsx`: 21 testes aprovados em dois arquivos, incluindo aplicação/limpeza dos filtros existentes.
- `npm run build` repetido após os ajustes e aprovado, incluindo compilação, TypeScript e páginas estáticas. OpenSpec estrito e diff check aprovados.
