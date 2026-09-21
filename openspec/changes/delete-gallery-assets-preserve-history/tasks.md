## 1. Histórico e invariantes
- [x] 1.1 Implementar migration aditiva e modelos de movimentos textuais, disponibilidade de pedido/grupo e limpeza durável; validar upgrade preservando dados e downgrade protegido.
- [x] 1.2 Implementar preparação idempotente sem transição financeira, preservando seleções, snapshots e grupos; validar todos os estados e concorrência PostgreSQL.
## 2. Exclusão
- [x] 2.1 Unificar limpeza de foto/pasta e privada, dependências e arquivos históricos, com isolamento e retentativa; testar avulsa, pasta, compartilhamento e falha física.
- [x] 2.2 Corrigir exclusão pública integral e retomada de operações antigas, inventário, locks e progresso; reproduzir falha de dependências e validar ausência do acervo com financeiro intacto.
## 3. Consulta e interfaces
- [x] 3.1 Expor movimentos e pedidos indisponíveis no histórico administrativo/cliente, impedir cobrança de rascunho removido e preservar decisões de grupos comunicados; testar autorização, filtros e regressões.
- [x] 3.2 Atualizar confirmações, rótulos e visualização textual sem links quebrados; testar frontend e build.
## 4. Entrega
- [x] 4.5 Organizar histórico administrativo sob consulta explícita, filtros e paginação no servidor, sem log na visão padrão; validar autorização, galerias sem pedido, paginação, interface e build.
- [x] 4.4 Corrigir recuperação da operação após reabrir a galeria; testar resumo autenticado, retomada explícita com inventário atualizado e ausência de nova exclusão/retentativa automática.
- [x] 4.1 Revisar diff, executar validações proporcionais backend/frontend/OpenSpec e preparar PR com evidências, preservando mudanças locais anteriores; parar quando só CI estiver pendente.
- [ ] 4.2 Após gates aplicáveis, publicar e verificar homologação; retomar Galeria 01 somente com autorização operacional, registrar saúde/escopo e aceite humano antes de sincronizar/arquivar.

## Context
Decisão aprovada pelo proprietário e implementação solicitada. Base local/remota `fff7a742`. Inspeção anterior somente leitura: Galeria 01 `cff9d256-bb0c-4158-89d2-3212f541fddd` em deleting, 2 pastas, 58 registros de foto, operação falha em removing_records após preparing_history/removing_storage. Não executar exclusão em homologação durante implementação local. Documentos sujos de outras changes e `.codex-tmp` devem ser preservados/excluídos dos commits.

## Evidências

- Migration 0059: teste de upgrade sobre 0058, downgrade vazio e recusa após registro durável passou em SQLite e PostgreSQL (21/09/2026). PostgreSQL usa banco sintético exclusivo criado no serviço local 127.0.0.1:55458, sem tocar dados de homologação.
- Integração PostgreSQL inicial: 20 testes de exclusão e checkout passaram; corrida real comunicar PIX × excluir foto passou. O conjunto dedicado de exclusão também passou com 8 casos, incluindo decisão administrativa após exclusão, notificações preservadas, filtros e isolamento por cliente.
- Regressão ampla inicial: 128 testes passaram; 10 expectativas da política anterior precisaram ser atualizadas. Reteste direcionado: 15 passaram e 1 ainda carregava o limite antigo de consultas. Reteste final desse limite com diretório de clientes, regiões faciais e purge: 32 passaram. A consulta adicional do histórico é em lote, sem N+1.
- Frontend: 90 testes passaram na primeira execução sequencial, com uma expectativa antiga sobre ausência de imagem ajustada; os 13 casos focados passaram depois. Após os avisos de limpeza pendente, os 62 testes de galerias/editor passaram. Build final (Next/TypeScript) passou; lint sem erros, com avisos preexistentes.
- OpenSpec estrito: 56 itens passaram; Ruff backend e git diff --check passaram.
- Integração final PostgreSQL: 25 testes passaram em 173,52 s, incluindo exclusão privada com uploads próprios e referência pública compartilhada, justiça da fila após falha, decisão financeira após exclusão e concorrência com comunicação. Migration PostgreSQL: 1 teste passou em 67,85 s. Nenhum skip nos 25 casos. Build final passou e lint final teve 0 erros/27 avisos preexistentes.

## Continuidade e gates

Branch `codex/delete-gallery-assets-preserve-history`, base `fff7a742`. Não sincronizar nem arquivar antes do aceite humano. Publicação/retomada operacional descritas em `homologacao.md`; nenhuma mudança no servidor ocorreu durante implementação. Quando o PR estiver publicado e só faltar CI, interromper e aguardar o usuário, sem polling do Actions.

Revisão final: 35 arquivos relacionados selecionados explicitamente; documentos preexistentes de outras changes e .codex-tmp excluídos do commit. Descrição do PR preparada com escopo, evidências e limitações de homologação.

## Correção do CI #272

- [x] 4.3 Reconciliar o teste de manifesto de ajuste de prévias com a exclusão integral aprovada, executar regressão do módulo e reenviar o PR.

Execução `35579081718` no commit `df1f8d5`: backend com 678 testes aprovados, 11 skips e uma falha em `test_lifecycle_manifest_includes_adjustment_and_preserves_private_reference`. A expectativa antiga removia todos os arquivos do manifesto quando havia referência privada; isso contradiz a política aprovada de exclusão da origem. Atualizar o teste para exigir original, prévias convencionais e ajustada no escopo, mesmo com referência privada. Nenhuma alteração na lógica de produto é necessária. Frontend, OpenSpec e gitleaks passaram nessa execução.

Validação da correção: `python -m pytest backend/tests/test_preview_adjustment.py -q --tb=short` — 22 aprovados em 179,36 s. Ruff completo de app/tests, OpenSpec estrito da change e diff check aprovados. Somente teste e este registro foram alterados; não há mudança adicional de código de produção. Atualização enviada ao PR #91; aguardar retorno humano sobre o próximo CI, sem polling ou deploy.

Deploy de develop verificado em 21/09/2026: execução 35592663503 e job deploy-homolog bem-sucedidos, servidor limpo em df1e1477, migration 0059, 13 serviços saudáveis e health checks públicos aprovados. Recursos externos intactos. Task 4.2 ainda exige retentativa administrativa da Galeria 01 (58 fotos/2 pastas, operação failed) e aceite real; ver homologacao.md.

Recuperação da interface: backend validou criação idempotente, cancelamento e resumo/retomada (3 casos aprovados) e isolamento/autenticação/última operação cancelada (1 caso aprovado em reteste, após alinhar expectativa ao 403 vigente). Frontend: 52 testes aprovados, incluindo reabrir a página e confirmar inventário antes de POST na operação antiga. Build/TypeScript aprovados, lint 0 erros/27 avisos preexistentes; Ruff e OpenSpec estrito aprovados. Nenhuma retentativa destrutiva remota executada; a correção será publicada na branch codex/fix-gallery-deletion-recovery.

## Histórico administrativo sob consulta

O proprietário confirmou que a exclusão da Galeria 01 funcionou e solicitou retirar o log aberto da página financeira. Implementação na branch `codex/filter-removed-gallery-history`, base `81399b3`: seletor Exibir, consulta administrativa independente, filtros por cliente/galeria/período, páginas substituídas de 25 movimentos e agrupamentos inicialmente recolhidos. O endpoint impõe máximo de 50, aplica filtros antes do limite e mantém ordenação por data/UUID. Galerias disponíveis vêm dos snapshots, inclusive sem pedido. A resposta financeira não carrega mais movimentos removidos. Nenhuma migration nem alteração remota nesta melhoria.

Evidências locais: 2 testes de filtros/autorização/paginação passaram em SQLite (31,43 s) e PostgreSQL (16,26 s), incluindo 55 registros com a mesma data distribuídos sem duplicação entre páginas, galeria sem pedido e limites inválidos. Regressão financeira: 2 testes passaram em 29,42 s. Frontend: 7 testes passaram em 20,76 s, incluindo consulta apenas após seleção explícita, recolhimento e substituição de páginas/filtros. Build/TypeScript passou; ESLint 0 erros/27 avisos preexistentes; Ruff e OpenSpec estrito aprovados.

Próximo gate: PR e CI; parar aguardando retorno do usuário quando só restar CI. Aceite do novo filtro em homologação permanece pendente, sem sincronizar ou arquivar antecipadamente.
