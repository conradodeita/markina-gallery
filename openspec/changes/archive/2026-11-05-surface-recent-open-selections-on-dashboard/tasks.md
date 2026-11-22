# Tasks

## 1. Projeção tenant-scoped da seleção atual

- [x] 1.1 Adicionar o campo nullable de início a `GalleryClientState` com migration aditiva, capturar o instante exato na primeira foto quando não houver seleção atual e expor no resumo os até cinco grupos tenant-scoped; testar migration, agregação, ordenação e isolamento. Evidência: teste da migration e `test_validation_summary_projects_recent_open_selections_per_tenant` aprovados.
- [x] 1.2 Testar que adicionar/remover fotos sem esvaziar o carrinho preserva o início, que esvaziar e iniciar outro carrinho define novo horário e que estados legados sem valor exibem ausência de horário; revisar que `first_selection`, pagamentos e dados anteriores não sejam reescritos. Evidência: `test_canonical_selection_start_tracks_each_new_cart` e teste frontend para início legado sem horário; migration nullable sem backfill, sem mudança no marco `first_selection` ou ciclo de vida financeiro.

## 2. Visão geral e destino contextual

- [x] 2.1 Mostrar os grupos atuais no card “Acesso recente” sem remover os links de galerias recentes; testar nome, galeria, contagem, horário e estado vazio. Evidência: testes do painel cobrem os estados preenchido e vazio, incluindo “Horário não registrado”.
- [x] 2.2 Gerar links com cliente, Galeria pública e fragmento do grupo efetivo; testar o destino exato e a preservação dos atalhos de galerias. Evidência: teste do painel verifica query/hash e atalhos de galerias preservados.

## 3. Vendas e pagamentos

- [x] 3.1 Interpretar o atalho contextual antes da primeira consulta, aplicando filtros exatos e “Todas” apenas quando cliente e galeria forem informados; testar que a entrada normal continua iniciando em pendências prioritárias. Evidência: testes verificam a consulta direta sem `financial_status` e a navegação normal com `priority`.
- [x] 3.2 Identificar e focar o cartão “No carrinho” correspondente após carregar; testar fallback para o cartão financeiro do cliente e estado vazio quando os dados mudarem. Evidência: testes focam o carrinho exato, o cartão financeiro alternativo e mantêm o filtro restrito no estado vazio.

## 4. Integração e revisão

- [x] 4.1 Validar os testes direcionados backend/frontend, lint, typecheck aplicável, OpenSpec estrito e `git diff --check`; revisar a área afetada segundo `docs/CONTINUOUS-REFACTORING.md` e registrar evidências e limites sem tocar em produção. Evidência: 3 testes backend, 29 frontend, ESLint, TypeScript, Ruff, OpenSpec estrito, validação de specs (24/24) e diff check passaram; detalhes e avisos em `validation.md`.
