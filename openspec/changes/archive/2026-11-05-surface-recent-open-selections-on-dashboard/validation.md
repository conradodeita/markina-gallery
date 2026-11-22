# Validação

Data: 2026-11-05. Execução somente local; nenhuma migration, dado, serviço ou configuração de produção foi alterado.

## Evidências

- Backend direcionado: 3 testes passaram (test_canonical_selection_start_tracks_each_new_cart, test_validation_summary_projects_recent_open_selections_per_tenant, test_gallery_client_selection_start_migration). O ciclo registra o início, preserva enquanto resta foto e inicia novo horário depois que a seleção esvazia; a consulta limita e isola os grupos por tenant; a migration aditiva preserva o estado anterior sem preenchimento histórico.
- Frontend direcionado: 29 testes passaram em app/admin/page.test.tsx e app/admin/payments/page.test.tsx, incluindo horários legados ausentes, atalhos de galerias, deep link, filtros, foco, fallback e estado vazio.
- ESLint nos quatro arquivos frontend alterados: passou.
- TypeScript npx tsc --noEmit: passou.
- Build otimizado do Next.js 16.4.2: passou numa cópia isolada dentro de frontend/build/codex-check-20261105. Arquivos de ambiente e dependências não foram copiados; a pasta .next do servidor de desenvolvimento foi preservada.
- Ruff nos módulos/testes backend alterados: passou. timezone.utc foi mantido para compatibilidade Python 3.10; as duas ocorrências receberam exceção localizada UP017.
- OpenSpec 1.14.0: validate surface-recent-open-selections-on-dashboard --type change --strict --no-interactive passou.
- Specs principais sincronizadas em gallery-sales/operational-gallery-interface e gallery-sales/payment-operations-dashboard; openspec validate --specs --strict --no-interactive passou em 24/24 specs.
- git diff --check: passou. Git apenas avisou que normalizaria line endings LF/CRLF em arquivos de trabalho já modificados; nenhuma conversão foi solicitada ou executada.

## Limites e decisões

- Seleções já ativas antes desta mudança podem não ter um horário exato. Não há reconstrução ou backfill; a interface informa Horário não registrado. O horário exato é capturado para novas seleções daqui em diante.
- O banco/API preservam UTC. Como não existe fuso configurado por tenant, o horário é convertido para o fuso local do dispositivo e a interface informa essa regra.
- A suíte reportou avisos preexistentes de depreciação do FastAPI e um aviso SQLAlchemy do ciclo de chaves estrangeiras na limpeza da base de teste. Os testes terminaram aprovados.
- A cópia de build isolada permanece em frontend/build/codex-check-20261105, ignorada pelo Git. A política automática do executor bloqueou a remoção, mesmo após conferir o caminho; o diretório .next do servidor original não foi alterado e a cópia não contém arquivos de ambiente.
- O proprietário aprovou a revisão humana em 2026-11-05. Após sincronizar as specs principais, a change foi arquivada conforme o fluxo OpenSpec.
