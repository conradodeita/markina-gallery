# Validação

## Inventário e fronteiras — task 1.1

- `backend/app/media_archive_storage.py` já define `delete_object(remote_id)` idempotente no protocolo injetável.
- `MediaArchiveCycle` já aceita `deleting`/`deleted`; `MediaArchiveOperation` já aceita `delete_remote`, mas `claim_next_operation` e `worker.py` só despacham `restore`/`archive`. Não há checkpoint por objeto nem lote agregado de exclusão.
- `gallery_lifecycle.py`/`gallery_cleanup.py` removem mídia local de galeria via operação própria e preservam histórico comercial; não removem nem comprovam ausência de objetos no arquivo frio. O fluxo novo não reutiliza nem duplica esse cleanup.
- `tenant_closure_recovery.py` agrega recuperação por ciclos e já calcula aniversário UTC de dez anos. Recuperação/reabertura precisam ser bloqueadas depois de mídia `deleted`; hoje o helper de recuperação considera esse estado concluído e será corrigido nesta change.
- `PhotographerBusinessProfile` possui fingerprint HMAC única e versão obrigatória. A impressão só será anulada após recibo completo de todos os objetos de todos os ciclos do lote; senhas, CPF em claro e IDs remotos não entram em eventos/respostas.
- `add-gallery-media-archive` já mantém expurgo automático fora da primeira versão e adia a operação `delete_remote` para uma change própria. Esta change implementa somente a decisão manual aprovada.
- O worktree possui extensa alteração preexistente não staged/untracked. Ela foi preservada; as mudanças desta change serão limitadas aos arquivos de escopo, sem limpeza, stage, commit ou push.
- Evidência estática coletada em 10/11/2026. Nenhum adapter real, Drive, banco persistente ou produção foi acessado.

## Preflight sem ciclos de arquivo — revisão de segurança

- A leitura do preflight em `backend/app/tenant_media_deletion.py` encontrou um caminho vazio que marcava o lote como concluído e removia `cpf_fingerprint` quando a conta não possuía ciclos cadastrados. Isso não provava ausência de bytes e contrariava a decisão de bloquear ciclos ausentes/legados sem prova.
- A implementação agora retorna `archive_proof_unavailable` antes de criar qualquer lote quando a conta não tem ciclos. A conclusão vazia e a limpeza imediata do CPF foram removidas; fingerprint e versão só são eliminados pelo recibo agregado após a conclusão de operações verificadas.
- Teste sintético em `backend/tests/test_tenant_media_deletion.py` usa mídia registrada sem ciclo: preflight e solicitação são bloqueados, nenhum lote é criado e o fingerprint permanece. A bateria focada passou.
- Ciclos arquivados com zero fotos ainda têm um manifesto remoto e podem ser excluídos com segurança; a validação do catálogo aceita o ciclo sem linhas de mídia, inclui o manifesto no inventário e confirma sua ausência. O worker avança o checkpoint de objetos mesmo quando a lista está vazia antes de excluir o manifesto. Teste sintético de arquivo e exclusão verifica esse caminho integralmente.

## Evidência de implementação e integração — checkpoint anterior ao PostgreSQL

- Backend: `backend/.venv/Scripts/python.exe -m pytest tests/test_tenant_media_deletion.py tests/test_platform_console_media_deletion.py tests/test_media_archive_worker.py tests/test_media_archive_executor.py tests/test_tenant_closure_recovery.py -q` — **59 passaram, 1 pulado**. Usa banco SQLite sintético em memória e adapter de storage sintético.
- Backend: Ruff nos módulos e testes de exclusão, worker, executor, console e recuperação — **passou**.
- Frontend: `npm test -- --run app/admin/platform/tenant-closure-console.test.tsx` — **7 passaram**; `npx tsc --noEmit` — **passou**; ESLint focalizado — **passou**.
- Integração frontend: `npm run build` — **passou**. `npm run lint` — **0 erros e 38 avisos** no repositório; avisos observados estão fora dos componentes desta mudança e não foram alterados nesta task.
- OpenSpec: `openspec validate add-audited-tenant-media-deletion --strict` — **válida**.
- OpenSpec global: `openspec validate --all --strict` — **153 passaram, 29 falharam** em outras changes/specs (avisos de requisitos extensos e conflitos preexistentes, entre outros). `add-audited-tenant-media-deletion` passou nessa mesma execução; mudanças alheias não foram alteradas.
- Migration PostgreSQL: `tests/test_tenant_media_deletion_migration.py` foi executado e ficou **pulado** porque `PHOTOGRAPHER_TEST_DATABASE_URL` não está configurada; o teste exige PostgreSQL sintético exclusivo. A validação de constraints, isolamento, upgrade e downgrade continua pendente; não foi usado o banco local existente nem infraestrutura compartilhada.
- Inventário read-only do ambiente confirmou ausência da variável, de `initdb`/`pg_ctl`/`postgres`/`psql`, e de container Docker publicado na porta de teste 15470. Nenhum container foi criado/iniciado; o bloqueio requer disponibilizar explicitamente o PostgreSQL descartável esperado pelo teste.
- Revisão estática da migration `20261110_0122_audited_tenant_media_deletion.py` confirmou que ela é aditiva e que o downgrade recusa remover auditorias, lotes, checkpoints ou perfis sem fingerprint. Ruff e `py_compile` passaram; isso não substitui a validação real em PostgreSQL.
- Refatoração contínua limitada à área afetada: removido o caminho de conclusão vazia e limpeza prematura do fingerprint; Ruff confirmou imports ordenados e sem import não usado. A fila e os adapters existentes continuam reutilizados; nenhum fluxo paralelo foi criado.
- Nenhuma chamada real ao Drive, banco persistente, Oracle ou produção; sem migration aplicada, deploy, stage, commit ou push.

## Checkpoint PostgreSQL concluído — 10/11/2026

- O proprietário autorizou preparar o banco temporário local. Docker confirmado em `desktop-linux`, daemon Linux local, porta 15470 livre. Os containers antigos parados foram preservados.
- Criados apenas containers novos com label `pyp.synthetic-test=audited-media-deletion`, `--rm`, limite de 768 MiB/1 CPU, tmpfs de 512 MiB em `/var/lib/postgresql/data`, sem volumes persistentes e porta `127.0.0.1:15470`. Imagem local fixada pelo ID `sha256:266d3c257594e195b309ae9d1805e54c788f1d7b375f56bf6c367aac6c917e7b`; `postgres --version` confirmou **17.11**. Credenciais aleatórias existiram só no processo/ambiente temporário e não foram escritas em `.env` nem no Git.
- A primeira execução revelou preparação incompleta do teste: o proprietário sintético precisava ser criado na revisão 0090 antes do gate de carteira 0094. Corrigido o fixture conforme os testes existentes, preservando o gate da migration.
- A execução PostgreSQL revelou um defeito real no retry: `attention_required` excedia o limite de 16 caracteres de `platform_admin_event.previous_status`, gerando HTTP 503. Modelo e migration local 0122 ampliam os dois estados para 32 caracteres; downgrade recusa perda/truncamento. O teste confirma o tamanho real no PostgreSQL e a gravação íntegra da auditoria de retry.
- O teste de dois workers usava o catálogo parcial da revisão 0112 com o ORM atual e falhava por coluna posterior ausente. Ele agora prepara a cadeia completa de migrations em schema sintético antes de testar o lock global; não foram acrescentadas colunas artificiais nem relaxadas proteções.
- Testes PostgreSQL de 0122 provaram preservação de dados legados, upgrade/downgrade vazio, par CPF/fingerprint consistente, negação de vínculo closure/tenant e operação/tenant divergentes, contagem inválida, vínculo válido e recusa de downgrade com lote, fingerprint removido, checkpoint remoto ou auditoria.
- Bateria final: `pytest tests/test_tenant_media_deletion_migration.py tests/test_tenant_media_deletion.py tests/test_platform_console_media_deletion.py tests/test_media_archive_worker.py tests/test_media_archive_executor.py tests/test_tenant_closure_recovery.py tests/test_tenant_closure_migration.py -q -rs` usando o Python do venv: **70 passaram, zero skips, 6 avisos conhecidos de lifespan**, em 164,34 s. Os testes de contrato que usam `client_db` também executaram em PostgreSQL nesta rodada.
- Cada container novo foi parado por ID após conferir sua label e removido automaticamente; nenhum volume persistente ou recurso antigo foi removido. Ruff passou nos arquivos alterados; frontend não mudou desde o checkpoint de testes/build registrado acima.

## Retry administrativo e ordem dos locks — 14/11/2026

- A revisão encontrou uma inversão potencial em `retry_media_deletion`: o endpoint bloqueava lote/operações antes do coordenador, enquanto o worker mantém o coordenador e bloqueia operação → ciclo → lote. Se retry e conclusão/falha disputassem a mesma operação, a rota podia aguardar a operação enquanto o worker aguardava o lote.
- A função agora bloqueia o coordenador global antes das linhas de tenant/lote/operação/ciclo. A regressão observa a ordem dos SELECTs com lock; falhava antes, com `batch` como primeiro lock, e passou depois com `coordinator` primeiro. `pytest tests/test_tenant_media_deletion.py -q -k deletion_retry_locks_global_coordinator_before_tenant_or_batch`: 1 aprovado.
- A evidência confirma a ordem do código sob SQLite sintético; não foi uma reprodução de deadlock real em PostgreSQL. Nenhum serviço foi iniciado nesta revisão.

## Estado final local

- Tasks 1.2 e 3.2 desbloqueadas e concluídas: **10/10 tasks** da change implementadas e validadas. `openspec validate add-audited-tenant-media-deletion --strict` passou no fechamento; a CLI confirmou 8 concluídas/0 restantes. As 29 falhas globais alheias já inventariadas não foram alteradas. Inventário final confirmou nenhum container com a label deste ensaio e porta 15470 livre.
- Nenhum acesso ao Drive real, Oracle, dados de clientes ou banco persistente; sem deploy, stage, commit ou push. Sync/arquivo continuam sujeitos à revisão humana prevista no repositório.

## Replay concorrente de ações do console — 14/11/2026

- As rotas consultavam `request_id` antes do lock da conta do proprietário. Se outra chamada confirmasse o mesmo pedido enquanto a segunda aguardava esse lock, ela podia repetir a mutação, tentar inserir uma auditoria com chave única já usada ou exigir um TOTP já consumido.
- As rotas agora consultam novamente o evento/lote depois do lock e antes do rate limit, TOTP e serviço. A regra cobre exclusão, retry, redução de perfil, recuperação em lote e reabertura; o helper rejeita replay com ator, tenant, ação ou resultado divergente.
- Testes HTTP injetam um evento/lote já confirmado logo após a consulta com lock e verificam resposta replay sem reautenticação ou chamada mutável: 5 casos passaram. A evidência sintetiza a janela de concorrência no SQLite; não é uma disputa HTTP/PostgreSQL real. Ruff e `py_compile` dos módulos/testes alterados passaram.
