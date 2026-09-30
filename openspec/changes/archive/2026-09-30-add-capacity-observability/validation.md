# Validação e continuidade — add-capacity-observability

## Aceite e baseline

- Aceite explícito em 2026-09-30: “Aprovo a proposta `add-capacity-observability`; pode iniciar a implementação local na branch isolada.”
- Implementação em `C:\codex-data\worktrees\capacity-observability\Photo Delivery`, branch `feature/add-capacity-observability`, base `abd4d21f8fec1efd0f18eb0a8eebe4c0f2444293`.
- Antes da implementação, o checkout isolado continha apenas os artefatos da change OpenSpec; nenhum trabalho anterior foi sobrescrito.
- Foram inspecionados `require_admin`, `require_single_tenant` e as proteções de propriedade facial. Permanecem como guardas; a nova rota não recebe tenant nem conta como entrada.

## Limites do aceite

Somente implementação e validação local da change. Não houve acesso a CI remota, OTP, dados remotos, endpoint diagnóstico publicado ou mutação em homologação. A página administrativa já autenticada pelo usuário foi observada em modo somente leitura e confirmou que a versão publicada ainda não contém a change. A validação visual e o PostgreSQL foram sintéticos locais, com autorizações explícitas posteriores. Não houve migration do produto, tuning, mudança de `.env`/segredo, deploy, publicação, push ou merge. Orçamento global continua nulo e os limites do processo não viram sizing. Após a revisão humana e a autorização explícita de 2026-09-30, a spec foi sincronizada e a change arquivada localmente.

## Evidências

- Contrato fechado, pool, consultas PostgreSQL agregadas, filas e orçamento indisponível: testes unitários sintéticos existentes em `backend/tests/test_capacity_observability_*.py`.
- Coletor/cache: SQLite em memória exclusivo por teste; teto observado de três SELECTs para filas em SQLite, ausência de `SELECT *`, cache de 30 segundos, cópia marcada como cache, expiração, exclusão mútua, `collection_busy`, isolamento de falha parcial e perda do cache ao limpar o estado em memória.
- Autorização: `test_facial_observability.py` verifica anônimo, papel cliente, administrador válido, cache preenchido, sessão revogada e tentativa de `tenant_id`; `test_tenant_auth.py` cobre vínculo ausente/revogado, instalação suspensa ou múltipla e contexto externo; `test_tenant_domain.py` verifica falha fechada sanitizada no middleware. A rota marca respostas, inclusive negativas, `Cache-Control: no-store`.
- Sanitização/efeitos: registro sintético com sentinelas em erro privado não aparece no snapshot nem nos logs capturados. Coleta SQLite foi instrumentada; apenas SELECT agregados foram executados. Pool reutiliza `engine.pool`; nenhuma chamada a provider, worker, filesystem ou Redis foi adicionada.
- Interface: testes Vitest cobrem estado inicial recolhido sem fetch, consulta manual, zero observado, nulos indisponíveis, remoção do snapshot após 403, recuperação e abort ao desmontar. A seção não contém polling nem controles de tuning. A inspeção visual local usou uma rota sintética temporária na porta exclusiva `43127`, removida após o teste, com dados fixos e sem chamar backend, OTP ou endpoint real. Em desktop, a seção recolhida/expandida, hierarquia, valores e controles ficaram legíveis. Em viewport 390×844, a primeira inspeção revelou rótulos do pool comprimidos; o breakpoint foi corrigido para empilhar termo e valor. A repetição confirmou leitura contínua das cinco filas e do orçamento até o botão “Atualizar agora”. O botão expôs estado recolhido/expandido na árvore de acessibilidade. A página administrativa já aberta em homologação foi apenas observada para confirmar que a versão publicada ainda não contém a nova seção; não foi usada como evidência da implementação e nenhuma ação de domínio foi executada.

## Validação PostgreSQL sintética

- Aceite adicional explícito em 2026-09-30 autorizou PostgreSQL Docker isolado. O inventário confirmou porta 55469 livre, nome exclusivo e imagem local `postgres:17-alpine`; o container `markina-gallery-capacity-postgres` usou somente loopback, `tmpfs`, nenhuma montagem, nenhuma rede/volume novo e nenhum arquivo `.env`. Um container antigo parado e containers de outros projetos permaneceram sem comandos direcionados. Ao final, `docker stop` atingiu somente o container sintético, que foi removido pelo próprio `--rm`; a porta ficou livre e o Docker Desktop retornou ao estado desligado encontrado no inventário inicial.
- `TENANT_TEST_DATABASE_URL` existiu somente no processo dos testes e apontou para `pyp_tenant_test` em `127.0.0.1:55469`. Nenhuma instância remota, compartilhada ou de homologação foi consultada.
- Corpus: 320 jobs de mídia, 32 análises, 240 ajustes de prévia e 480 jobs faciais, além de uma tabela mínima para contenção de lock. O coletor executou cinco SELECTs, retornou cardinalidade fixa de cinco filas e teve os cinco planos aceitos por `EXPLAIN (FORMAT JSON)`.
- A rodada integrada final registrou 0,109910 segundo; uma rodada anterior registrou 0,153225 segundo. Esses tempos são evidência do teste sintético, não capacidade, benchmark de produção ou SLO.
- `SET TRANSACTION READ ONLY`, statement timeout de 500 ms, lock timeout de 100 ms, rollback/liberação e ausência de vazamento para a próxima sessão foram comprovados. A simulação de permissão insuficiente tornou a seção PostgreSQL indisponível com `permission_denied` e preservou as filas autorizadas. Banco atual permaneceu subconjunto das conexões visíveis, a conexão da coleta integrou a observação, reservas legíveis foram retornadas e a ausência de campo continuou coberta como indisponível pelos testes unitários.

## Implementação local e validação

- O coletor reutiliza `engine.pool`, faz até cinco SELECTs agregados, abre sessões curtas, aplica `SET TRANSACTION READ ONLY` e timeouts locais em PostgreSQL e isola falhas por seção. Cache, limite por processo e resposta indisponível do orçamento global foram implementados sem estado persistente.
- A rota `GET /admin/capacity-observability` executa `require_admin` antes do cache. Middleware também aplica `Cache-Control: no-store` aos erros de contexto que ocorrem antes do endpoint. O service worker já ignora `/api/`.
- A Visão geral `/admin` contém seção recolhida, sem polling; a consulta é sob demanda, com atualização manual, abort ao desmontar, motivos sanitizados e remoção do snapshot após falha. A documentação de acesso está em `docs/admin-capacity-diagnostics.md`.
- `python -m pytest` dos contratos, pool, banco, filas, orçamento, coletor, observabilidade facial, autorização e domínio com PostgreSQL sintético: **59 passed, 1 deselected**. O teste excluído, `test_tenant_domain.py::test_revogacao_durante_render_nao_publica_arquivo`, reproduz isoladamente `sqlite3.OperationalError: database is locked` quando uma sessão peer tenta suspender o tenant durante uma transação SQLite ativa; não executa o diagnóstico nem usa seus arquivos. Os demais testes do mesmo módulo passam. O teste foi mantido intacto e a falha não foi atribuída à change. O processo do pytest terminou com sucesso, mas o callback de limpeza do diretório temporário em `%TEMP%` também emitiu `PermissionError` no Windows.
- `ruff check app tests`: passou. `npm run lint`: terminou sem erros (37 avisos do repositório); `npx tsc --noEmit`: passou; `npm run build`: compilou e gerou as 22 páginas estáticas/dinâmicas.
- `npm test`: **51 arquivos e 366 testes passaram**. Os testes novos cobrem seção recolhida, consulta única sob demanda, atualização, cache, zeros, indisponibilidade, evidência estimada, falha de rede, 403, teclado e cancelamento ao desmontar. A suíte PostgreSQL focada passou com 4 testes; a regressão relevante de backend passou com 59 testes e nenhum skip.
- `npx --yes @fission-ai/openspec validate add-capacity-observability --strict --json`: 1/1 válido. `npx --yes @fission-ai/openspec validate --all --strict --json`: 73/73 artefatos válidos; houve apenas um aviso `INFO` preexistente em outra change.
- O teste SQLite instrumentado viu três SELECTs de filas, sem `SELECT *` ou DML. Sentinelas sintéticas em `MediaJob.last_error` e em erro injetado não aparecem na resposta nem nos logs capturados; o estado, attempts e erro do registro ficam iguais antes/depois. A semântica específica do PostgreSQL está coberta separadamente pelos quatro testes locais descritos acima.

## Revisão do diff

- O diff local contém somente o coletor e os contratos do diagnóstico, rota/middleware no backend, seção da `/admin`, documentação, testes relevantes e os artefatos desta change. Não há alteração em `.env`, segredos, dependências, migration, configuração do pool ou infraestrutura. A instalação de dependências não alterou o lockfile; saídas de build e caches permanecem ignoradas.
- Revisados os contratos de resposta e as consultas: não serializam identidade, caminho, SQL em execução, payload, token ou dado biométrico; o endpoint preserva as guardas atuais e o resumo administrativo/facial anterior.
- A branch isolada permanece sem arquivos staged e sem commit. A revisão humana foi registrada em 2026-09-30, seguida de autorização explícita para sincronizar e arquivar.
- A nova spec consolidada `deployment-operations/admin-capacity-diagnostics` preserva integralmente os sete requisitos e 23 cenários do delta. A comparação exata do bloco normativo passou, as 12 specs passaram em modo estrito e a change foi movida para `openspec/changes/archive/2026-09-30-add-capacity-observability` com seus metadados preservados.
- Depois do arquivamento, `openspec validate --all --strict --json` passou com 73/73 itens e `openspec list --json` confirmou que `add-capacity-observability` não está mais entre as changes ativas. Deploy continua fora do aceite.

## Pendências externas à implementação

- As tasks 2.2 e 4.1 foram concluídas; não resta bloqueio de implementação desta change.
- A task 5.2 foi concluída com inspeção visual sintética local e correção responsiva. Depois da correção, `vitest` focado passou com 6 testes, `eslint --quiet` passou, o build gerou 22 páginas e `tsc --noEmit` passou. A rota e os artefatos temporários de desenvolvimento não integram o diff.
- O teste SQLite de revogação durante render permanece uma falha ambiental preexistente documentada acima e requer investigação no ambiente que suporte a concorrência de gravação desse teste.
- A revisão humana, a sincronização da spec e o arquivamento foram concluídos em 2026-09-30. Publicação, push/merge e deploy permanecem fora do aceite e exigem autorização própria; deploy também exige inventário e plano de impacto zero.
