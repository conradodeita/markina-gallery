# Validação

## Regressões na apresentação de pagamentos — 12/11/2026

### R2 — pedido histórico confirmado sem comunicação

- A migration que introduziu `PaymentCommunication` não faz backfill de pedidos legados. Portanto, ausência desse registro não prova que a cliente deixou de comunicar o pagamento; o estado persistido do `SaleOrder` continua sendo a fonte de confirmação.
- No detalhe de Vendas e pagamentos, pedidos confirmados sem comunicação agora mostram “Pagamento confirmado no histórico.”. O teste do cenário confirma que a mensagem anterior “A cliente ainda não comunicou o pagamento.” não aparece.
- A revisão autenticada local em `3044` confirmou a mensagem no detalhe do pedido sintético. Nenhuma decisão, valor ou estado financeiro foi alterado.

### R3 — seleção finalizada sem cobrança

- Antes da correção, a seleção cujo pedido tem `payment_status=not_required`, snapshot `payment_required=false` e `frozen_at` era incluída no painel financeiro e classificada como `awaiting_payment`. O teste integrado reproduziu esse estado.
- O backend agora retorna `selection_finalized` somente quando esses três critérios indicam uma finalização externa válida. O filtro de estado aceita a categoria, o filtro “Aguardando pagamento” não inclui esse pedido e a seleção não é contabilizada como receita confirmada.
- O painel apresenta “Seleção finalizada sem cobrança”, não mostra R$ 0,00, não afirma que a cliente deixou de comunicar pagamento e reconhece link de entrega publicado como “Fotos disponíveis”. A biblioteca do cliente já usa `selection_finalized`, sem mensagem “Aguardando pagamento”; os testes existentes preservam esse contrato.
- Validação local: `python -m pytest -q tests/test_unified_checkout.py -k canonical_external_selection_api_admin_export_and_history` — 1 aprovado; `python -m ruff check app/main.py tests/test_unified_checkout.py` — aprovado; teste frontend focado `npm test -- app/admin/payments/page.test.tsx --maxWorkers=2` — 19/19; ESLint dos dois arquivos — aprovado; `npx tsc --noEmit --pretty false` — aprovado; `npm run build` — compilação, TypeScript e 27 páginas geradas. O frontend e dependências foram validados em cópia isolada `C:/codex-data/visualizations/2026/11/12/saas-release-audit/frontend-review-3044`; o worktree não foi reinstalado nem reconstruído.
- A execução inicial vermelha reproduziu `awaiting_payment`; após a correção, o teste integrado passou. Os avisos do teste backend são warnings de eventos de ciclo de vida do FastAPI e dependências circulares da fixture SQLite.
- Revalidação integrada da fronteira de `main.py` em 12/11: quatro casos passaram — `test_external_selection_is_frozen_without_pix_payment_or_revenue`, `test_canonical_external_selection_api_admin_export_and_history`, `test_client_interactions_are_private_reversible_and_audited` e `test_expired_selection_and_foreign_client_interactions_are_denied` (4 aprovados, 10 avisos). A evidência confirma finalização sem cobrança/estado de espera indevido e comentário/favorito escopados ao cliente autorizado. Essa bateria é complementar; não substitui a suíte completa no SHA integrado.

## Validação OpenSpec

- `openspec validate complete-gallery-operational-flow --strict` — change válida.
- `openspec validate improve-gallery-and-client-data-lifecycle --strict --json` passou após a atualização: 1/1 válido, sem warnings ou erros; emite somente um aviso informativo porque a spec consolidada não contém o cabeçalho `Configuração administrativa do modo de acesso e modelo herdado` referenciado pelo delta `MODIFIED`. Esse delta antigo ainda precisa ser reconciliado antes de sincronizar/arquivar; a change aguarda revisão humana.

## Preparação do inventário e do plano de impacto zero para a task 8.6 — 12/11/2026

- A decisão do proprietário em `add-small-multi-photographer-pilot/design.md`, de 11/11/2026, define o servidor de produção existente como destino do SaaS e declara que não há homologação separada. Essa decisão substitui o alvo de homologação do inventário histórico de 31/08/2026; a autorização antiga não cobre produção.
- Consulta SSH somente leitura de 12/11/2026 no projeto Compose `markina-gallery`: 13/13 containers `Up` e `healthy`; Nginx do app em `127.0.0.1:8080 -> 80/tcp`; API/web/banco/Redis sem portas publicadas diretamente no host; `alembic current` na API = `20261026_0090 (head)`. O checkout remoto estava em `0dd015a62447e0c8d4c6af16b381140c8118f2ec`, sem mudanças em `git status`; branch não retornada (checkout destacado).
- Estado local no momento da consulta: branch `feature/saas-release-candidate`, HEAD `855be42b826c61c8ebdb2bd1e471ca1d28147061`, Alembic head `20261111_0125` e 697 entradas em `git status --short --untracked-files=all`. Não existe SHA isolada de candidato nesta etapa; nenhuma mudança local foi descartada.
- Foram consultados apenas saúde/portas de containers, SHA/status do checkout remoto e revisão Alembic. Não foram lidos dados de clientes, segredos, configuração `.env`, logs, backups ou mídias; proxy externo, endpoints HTTP, integridade/restauração de backups e impacto real de locks continuam desconhecidos.
- **NO-GO para a execução da task 8.6 neste momento:** schema produtivo e local divergem por 35 revisions (`0090→0125`); há worktree amplo sem candidato isolado; o backup/restore atual não foi comprovado; o fluxo de release API/web existente proíbe migrations, Compose e workers; e a validação 8.6 escreve e exclui dados, portanto exige autorização operacional específica. A saúde dos containers não prova impacto zero.
- Plano: preservar o worktree; completar o gate pré-push de 100%; isolar e revisar o SHA; validar a cadeia `0090→0125` em PostgreSQL descartável; comprovar backup/restore; aprovar fluxo de release que inclua exatamente migrations e runtimes necessários; repetir inventário no SHA exato; obter autorização específica antes de qualquer operação em produção; manter signup fechado e usar somente dados do proprietário estritamente sintéticos. Se alguma etapa exigir interrupção não aprovada, parar antes de executá-la.
- Nenhuma publicação, migration, escrita ou exclusão em produção, reinício, mudança de segredo, proxy, DNS ou recurso de terceiro ocorreu. A task 8.6 permanece aberta. Em 12/11/2026 o proprietário aprovou classificá-la como aceite operacional pós-release, fora do percentual de prontidão pré-release de 100%. Isso não reduz os demais gates locais nem autoriza publicação ou operação em produção.

## Limites e segurança

- Toda a verificação ocorreu em ambiente local com conta e pedidos sintéticos; nenhum dado real de cliente foi usado. Não houve SSH, operação, leitura de dados ou alteração de serviço em produção.
- As capturas foram inspecionadas na saída visual do CUA. O fluxo de controle não forneceu caminho para persistir os PNGs no worktree; o resultado visual e a navegação observados estão descritos nas evidências da task 4.4.
- Desvio de sequência OpenSpec: a task e o cenário delta da R3 foram registrados antes do código; a proposta e a decisão técnica correspondentes foram reconciliadas depois da primeira implementação local, nesta mesma change. Não houve efeito externo.
- Nenhuma spec principal foi sincronizada, change arquivada, migration executada, build publicada, commit ou push realizado.

## Revalidação da documentação OpenSpec — 12/11/2026

- O fluxo CI em `.github/workflows/ci.yml` executa `openspec validate --strict --all`; portanto, warnings de requisitos longos são um gate real do GitHub.
- A varredura local encontrou 73 warnings de requisitos acima de 500 caracteres em 28 artefatos e dois avisos informativos de delta `MODIFIED` sem requisito consolidado. O relatório JSON está fora do Git em `C:/codex-data/visualizations/2026/11/12/saas-release-final/openspec-strict-all-current.json`.
- Nesta change, quatro requisitos longos foram reescritos de forma concisa, preservando os cenários e as regras normativas. `openspec validate improve-gallery-and-client-data-lifecycle --strict --no-interactive` passou; resta somente o aviso informativo do requisito `MODIFIED`, cuja sincronização aguarda revisão humana. `git diff --check` passou com avisos de normalização LF/CRLF.
- Recontagem da worktree: 700 caminhos pendentes (186 modificados rastreados, 514 não rastreados), zero staged; o diff rastreado soma 12.294 linhas adicionadas e 1.587 removidas. O inventário exato e ownership dos hunks continuam pendentes; não houve commit, push ou operação externa.

## Revalidação global do gate OpenSpec — 12/11/2026

- A nova execução de `npx -y @fission-ai/openspec@1.14.0 validate --strict --all --json` terminou com exit code 0: **186/186 itens válidos, zero warnings e zero erros**. Permaneceram nove mensagens informativas sem bloqueio.
- O relatório JSON foi salvo fora do repositório em `C:/codex-data/visualizations/2026/11/12/saas-release-final/openspec-strict-all-after-doc-batch3.json`.
- Os ajustes documentais nesta rodada removeram avisos de requisitos longos e corrigiram o cenário ausente encontrado durante a execução anterior; não alteraram código de produto. Nenhum teste de aplicação foi executado nesta etapa.
- A worktree passou a ter 718 caminhos pendentes (204 modificados rastreados, 514 não rastreados), zero staged; o diff rastreado soma 12.391 inserções e 1.631 remoções. Esses números incluem trabalho preexistente e não equivalem a um manifesto de candidato aprovado.
- A validação OpenSpec deixa de ser bloqueio local conhecido para o workflow de CI, mas não comprova CI remota, integração do candidato, revisão por hunk, compatibilidade de migrations, backup/restauração, rollback ou prontidão de publicação. Não houve commit, push ou alteração externa.
- Gitleaks 8.24.3, versão fixada em `.github/workflows/ci.yml`, examinou os 718 caminhos modificados/não rastreados da worktree: zero achados. O relatório sanitizado (sem valores de segredo) está em `C:/codex-data/visualizations/2026/11/12/saas-release-final/reconciliation/gitleaks-current-worktree-summary-20261112.json`; a cópia temporária e o relatório bruto foram removidos. O job GitHub usa `gitleaks git -v` no histórico completo, portanto esta varredura local não o substitui.
