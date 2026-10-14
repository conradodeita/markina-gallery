# Tasks

## 1. Busca financeira por telefone e identidade selecionada

- [x] 1.1 Adicionar testes backend para busca parcial por nome/telefone, filtro exato por cliente, seleções abertas, pedidos e combinação com paginação/filtros existentes; confirmar que respostas financeiras não passam a serializar telefone.
- [x] 1.2 Implementar os critérios na consulta `GET /admin/payment-communications` com parâmetros opcionais compatíveis; executar os testes direcionados do dashboard financeiro.

## 2. Sugestões de cliente no filtro existente

- [x] 2.1 Adicionar testes de componente para debounce/cancelamento, sugestões por nome e telefone, seleção exata, edição posterior do texto, teclado, Escape, estado vazio e erro; confirmar que não há segundo campo de busca.
- [x] 2.2 Integrar as sugestões ao endpoint administrativo existente de clientes e permitir selecionar uma identidade exata mantendo os outros filtros; executar os testes direcionados do painel.

## 3. Filtro sticky e integração responsiva

- [x] 3.1 Reposicionar o filtro atual antes dos resumos e listas, manter a busca Cliente/telefone na faixa compacta e fixar a faixa abaixo da navegação administrativa; validar larguras mobile e desktop, foco, camadas e ausência de sobreposição.
- [x] 3.2 Executar os testes frontend/backend focados, lint, typecheck, build aplicável, `openspec validate --strict` e `git diff --check`; registrar resultados sem alterar artefatos ou arquivos locais preexistentes não relacionados.

## Evidências de validação

- Backend: `pytest backend/tests/test_derived_galleries.py -q -k 'admin_payment_dashboard_groups_orders_uses_snapshots_and_paginates_without_n_plus_one or admin_payment_dashboard_combines_validated_filters or admin_payment_dashboard_searches_phone_and_exact_client_without_exposing_phone'` — 3 passaram. Inclui paginação existente, busca por dígitos do telefone, identidade exata nas seleções/pedidos e ausência do telefone na resposta.
- Frontend na branch atual de `develop`: `npm test -- --run app/admin/payments/page.test.tsx --reporter=dot` — 10 passaram. Cobrem debounce/cancelamento, sugestões por nome e telefone, seleção/edição, teclado, Escape, vazio/erro, campo único, posição no DOM e ajuste ao cabeçalho medido.
- Qualidade frontend: `npx eslint app/admin/payments/page.tsx app/admin/payments/page.test.tsx` e `npx tsc --noEmit` — passaram.
- Build na branch atual de `develop`: `npm run build` — passou, incluindo compilação, TypeScript e geração das 23 páginas estáticas.
- OpenSpec: a change passou em `validate improve-payment-dashboard-search-and-sticky-filters --strict` antes do arquivamento; após a sincronização, `validate --specs` — 20 specs passaram com avisos de requisitos longos já existentes.
- Diff: `git diff --check -- backend/app/main.py backend/tests/test_derived_galleries.py frontend/app/admin/payments/page.tsx frontend/app/admin/payments/page.test.tsx frontend/app/globals.css openspec/changes/improve-payment-dashboard-search-and-sticky-filters` — passou.
- Layout: o filtro é irmão do formulário avançado dentro do contêiner que cobre todo o painel, para não parar no fim do formulário. `ResizeObserver` atualiza o `top` conforme a altura real da navegação; a navegação usa `z-index: 5`, a faixa `z-index: 4`, e as sugestões limitam a altura a `45vh` com rolagem interna.

## Workflow follow-up

- Revisar a proposta com o proprietário antes de implementar, conforme `INSTRUCOES_EXECUTOR_CLAUDE_CODE.md`.
- Após implementação e validação, sincronizar o delta aprovado e arquivar a change somente após revisão humana; não fazer deploy sem autorização específica.
