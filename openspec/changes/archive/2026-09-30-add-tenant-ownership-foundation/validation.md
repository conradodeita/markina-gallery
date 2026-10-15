# Validação e continuidade

## Estado em 2026-09-29

Planejamento revisado e implementação local autorizada pelo proprietário. A aplicação está em andamento no worktree gerenciado indicado abaixo. Nenhum deploy ou descarte remoto foi executado. A lista atual inclui uma task adicional de compatibilidade da limpeza, conforme a orientação do proprietário de preservar admin/acesso/Evolution.

## Evidências do planejamento

- CLI OpenSpec 1.13.2 já disponível no cache npm local, utilizada diretamente via Node; nenhuma instalação necessária.
- `openspec validate add-tenant-ownership-foundation --strict --json`: exit code 0; uma change aprovada, zero issues.
- `openspec status --change add-tenant-ownership-foundation`: quatro de quatro artefatos de planejamento presentes. Esse resultado não significa implementação concluída.
- Conferência de links relativos e espaços finais dos sete Markdown de planejamento: zero problemas.
- Comparação SHA-256 dos 28 arquivos preexistentes capturados no baseline da auditoria: zero alterações. Manifest externo: `C:/codex-data/audits/PYP-ELASTIC-20260929/existing-work-baseline.json`.
- `git diff --check`: exit code 0; somente avisos preexistentes de normalização LF/CRLF, sem erro de whitespace.
- Código, `.env`, segredos, banco e infraestrutura não foram alterados; nenhum commit, push ou deploy foi feito.

## Situação histórica após o planejamento

Testes de produto, migration PostgreSQL, lint, typecheck, build, CI e smoke tests remotos dependem da implementação. A validação OpenSpec acima verifica os documentos; não comprova funcionamento ou isolamento em runtime.

## Gates registrados no planejamento inicial

1. Revisão da proposta e nova solicitação para aplicar a change, conforme a fronteira de planejamento da skill `openspec-propose`.
2. Na aplicação, começar pelo inventário 1.1, identificar a cadeia de código/migrations em 1.2 e seguir pelas tasks acionáveis com evidência por task.
3. Antes do remoto, conferir a revisão real do destino e reconciliar a diferença documental entre checkout 0061 e BENCH 0068. O servidor não foi inspecionado nesta preparação.
4. Deploy depende de release concreta, inventário atualizado, janela/backup/reversão e autorização explícita. Merge/push que acione o workflow de homologação integra esse gate.

Use `delivery-plan.md` para comunicar cada entrega ao proprietário. Não apresentar esta fundação como conclusão de P0.1, como B01 aprovado ou como habilitação de outro fotógrafo.

## Aplicação iniciada — baseline e cadeia reconciliada

Autorização de implementação: proprietário solicitou iniciar após apresentação da proposta. A implementação ocorre no worktree gerenciado `C:/codex-data/worktrees/tenant-ownership/Photo Delivery`, branch `feature/add-tenant-ownership-foundation`. O checkout original e seus 28 arquivos preexistentes modificados permanecem preservados.

Fonte escolhida: `origin/develop` atualizado por fetch, SHA `04c6bb98cdbb7607026cd54106d9e4cdf43d1e29`. A árvore contém as migrations 0062–0068 ausentes no checkout original `95dbab718b5f0b705fa127d86649b308dba8ba36`. `python -m alembic heads`, executado em `backend/`, confirmou head único `20260928_0068`. A revision nova terá esse ancestral.

Inventário de produtores verificado por `rg` em `backend/app` e scripts Python: origem em `main.create_parent_gallery`; galeria privada em `private_membership._create_legacy_compatible_gallery`; fotos nas rotas de registro de capa e de foto da pasta em `main.py`. Workers não constroem essas três entidades nesta fonte: processam jobs, derivados, análise e notificações de fotos já registradas. Imports/clones reutilizam os produtores acima. Não foram encontrados inserts SQL em lote dessas três entidades no código de produto.

Autoridade: `auth.current_session`, `auth.create_session`, rotas administrativas e middleware da API; processamento: worker geral, fila facial e ajuste opcional. Efeitos que exigem revalidação: publicação de derivados/índice/busca, entrega WhatsApp/e-mail/push e lifecycle/cleanup. Testes devem cobrir entrada e revalidação após trabalho demorado.

Infra de teste local: container novo e exclusivo `pyp-tenant-test-20260929`, PostgreSQL 17, porta `127.0.0.1:55469`, banco sintético `pyp_tenant_test`. Nenhum container, volume ou rede preexistente foi alterado. `pg_isready` aprovou. A primeira invocação de Alembic pela raiz falhou por caminho relativo; foi corrigida executando em `backend/`, sem alteração de configuração.

### Inventário remoto inicial somente-leitura

SSH somente-leitura confirmou schema `20260928_0068` e uma conta administrativa. Nginx exclusivo publica `127.0.0.1:8080`; PostgreSQL/Redis não publicam portas. Há API, web, worker geral, três classes faciais e ajuste opcional. Evolution tem API, PostgreSQL 15 e Redis próprios, sem publicação externa. Firefly/Clearbudget, Nginx Proxy Manager e Portainer são vizinhos preservados. A identificação do SHA e dos volumes do destino continua na task 6.1.

### Autorização de descarte em homologação

O proprietário informou que os dados atuais do servidor podem ser descartados, preservando admin, acesso e Evolution conectada. O plano operacional deverá preservar credenciais/TOTP/sessões administrativas, configurações e volumes da Evolution, entradas de acesso HTTPS/proxy e configurações seguras do servidor. Essa autorização não implica apagar recursos de terceiros nem dispensar apresentação do inventário/plano antes da ação. Nenhuma limpeza remota foi executada. A migration continua não destrutiva e seus testes preservam o legado; eventual limpeza operacional usa o procedimento explícito da homologação.

### Task 2.1 — modelo

`TENANT_TEST_DATABASE_URL` apontando exclusivamente ao PostgreSQL sintético local, `python -m pytest tests/test_tenant_foundation.py -q`: **5 passed**, 17,89 s. Cobertura: `tenant_id` obrigatório/sem default, galeria de outro proprietário, foto de outro proprietário, foto privada em origem incompatível e persistência válida com UUIDs preservados. Schemas temporários próprios são removidos pelo teste, sem acessar outras bases. Aviso preexistente de permissão no cleanup do diretório temporário global do pytest não afetou o exit code 0; os próximos testes usarão diretório temporário exclusivo.

### Task 2.2 — migration

Revision `20260929_0069`, ancestral confirmado `20260928_0068`. O primeiro ensaio integrado teve **4 passed / 2 failed** em 62,83 s: PostgreSQL vazio/legado/inconsistente e SQLite vazio passaram; duas fixtures SQLite usavam UUID diretamente em colunas refletidas como CHAR. Corrigida exclusivamente a fixture. Reexecução focada SQLite legado/inconsistente: **2 passed**, 25,75 s. Assim, os seis cenários foram aprovados em seus respectivos bancos. O teste compara todas as colunas preexistentes de todas as tabelas antes/depois, incluindo hash/TOTP e sessão sintéticos, IDs, valores comerciais, referências e relações. Conferência órfã falha antes do DDL e mantém head 0068/schema intacto; downgrade de dados atribuídos é recusado. Os testes criam/remove apenas bancos `tenant_migration_<uuid>` no container local exclusivo.

### Task 2.3 — seed e fixtures

`pytest tests/test_tenant_foundation.py tests/test_auth.py -q` com banco de integridade PostgreSQL local: **23 passed**, 87,69 s. Seed cria vínculo na mesma transação e mantém hash/TOTP/id ao repetir; vínculo revogado ou ausente é recusado sem reparo. Os construtores legados de 38 arquivos de teste receberam propriedade explícita; `tests/tenant_fixtures.py` centraliza apenas o UUID sintético e a montagem de vínculo do administrador. O hook de seed de metadata está restrito às suítes legadas, excluindo os testes `test_tenant_*`; não altera comportamento de produto nem preenche propriedade em requisições/API. Ruff dos arquivos novos/principais passou após organização de imports. Nenhuma credencial real foi usada.

### Task 2.4 — compatibilidade da limpeza

As tabelas `tenant` e `tenant_admin` foram classificadas como preservadas na lista fechada existente. `pytest tests/test_tenant_migration.py -k limpeza`: **1 passed / 1 skipped**, 8,36 s; o skip é somente SQLite, porque a limpeza exige PostgreSQL. No banco PostgreSQL descartável, o teste removeu os dados operacionais e mídia sintética, preservando conta/vínculo, credenciais e sessão administrativas e a configuração do canal. A primeira fixture omitia `environment` do canal; corrigida e adotado NullPool para fechamento de conexões mesmo em falhas. Não há nova rotina de limpeza nem operação remota.

### Inventário remoto complementar

Leitura confirmou checkout `/opt/markina-gallery`, SHA `04c6bb98cdbb7607026cd54106d9e4cdf43d1e29`, Git sem mudanças, schema 0068, canal `ready`, 12 galerias, 3.214 fotos e uma cliente. Recursos preservados: `markina-gallery_pgdata`; volumes Evolution `markina-gallery_evolution-instances`, `markina-gallery_evolution-pgdata`, `markina-gallery_evolution-redisdata`; configuração HTTPS existente. API monta volumes próprios de source/derivatives/history/facial-references/branding. Nenhum valor de segredo, telefone ou sessão foi exposto.

### Task 3.1 — sessões e contexto

`pytest tests/test_tenant_auth.py -q` em PostgreSQL sintético: **7 passed**, 18,47 s. Sessão persistida anterior ao contexto é aceita com vínculo válido; revogação/ausência de vínculo, suspensão/segunda conta e instalação sem conta são recusadas. Header/query de tenant não substituem a autoridade da sessão. Criação de nova sessão administrativa também valida vínculo; cookie opaco e contrato de autenticação permanecem os mesmos. A regressão senha/TOTP da task 2.3 será repetida no checkpoint integrado após os gates HTTP.

### Task 3.2 — gates de domínio e workers

`pytest tests/test_tenant_domain.py -q` em PostgreSQL sintético: **7 passed**, 21,04 s. API mantém health disponível, mas recusa domínio com ausência, suspensão ou segunda conta. Worker geral, mídia, e-mail, WhatsApp, push, ajuste e claim facial recusam antes do trabalho. Sessões de domínio revalidam no commit; processamento facial revalida leases e propagação de contexto sem consumir tentativas extras; render revalida antes da publicação atômica e remove seu temporário quando bloqueado. Teste revoga durante render e após claim: sem prévia publicada, com job/lease durável preservado. Limpeza de lifecycle e high-res revalida antes de cada remoção; teste confirma arquivo intacto com contexto revogado. Envios revalidam imediatamente antes do provider, sem nenhum envio real no teste. Lint Ruff dos pontos alterados aprovado. A proteção é transitória para instalação única, não isolamento completo de múltiplos fotógrafos.

### Task 4.1 — origem administrativa

`pytest tests/test_tenant_producers.py tests/test_derived_galleries.py -k "origem_recebe or public_gallery_materializes" -q`: **2 passed**, 91 deselected, 9,21 s. Novo caso PostgreSQL cria/edita pelo contexto administrativo, ignora tenant de body/header, preserva UUID/proprietário e recusa edição após revogação do vínculo. Regressão SQLite de criação/materialização do preset aprovada. Produtor único `main.create_parent_gallery` define explicitamente propriedade; resolvedor de mutabilidade verifica origem persistida.

### Task 4.2 — galerias privadas

`pytest tests/test_tenant_producers.py tests/test_private_membership.py -q`: **7 passed**, 39,22 s. Produtor único `_create_legacy_compatible_gallery` herda `parent.tenant_id`; resolvedor transacional revalida a origem antes de criar/reusar. Caso PostgreSQL confirma individual, compartilhamento, retry e suspensão; regressões de membership legadas aprovadas. Referências/clones usam esse mesmo resolvedor; não há novo construtor nem cópia de storage.

### Task 6.1 — inventário remoto somente-leitura

Em 2026-09-29, nova leitura SSH confirmou SHA `04c6bb98cdbb7607026cd54106d9e4cdf43d1e29` e checkout limpo; schema 0068 pertence à cadeia alvo 0069. API/web/worker, três workers faciais, ajuste, nginx, PostgreSQL/Redis e Evolution saudáveis. Evolution consultada por endpoint de inventário, sem envio: **1 instância, estado `open`**; nenhum identificador/telefone/token foi impresso. HTTP local `/healthz` e `/api/health` e HTTPS público `/healthz`: **200**. Somente nginx publica `127.0.0.1:8080 → 80`; API8000/web3000/DB5432/Redis6379/Evolution8080 são internos. Memória disponível 18.975 MiB de 23.988 MiB; disco livre 126.915.518.464 bytes. Inventariados os volumes exclusivos pgdata, redisdata, media-source, media-derivatives, media-history, facial-references, branding-assets e os três Evolution. Nenhum recurso foi alterado. Inventário deve ser revalidado imediatamente antes de execução autorizada; esses resultados não são aceite de deploy.

### Task 4.3 — registro de fotos

Todos os produtores inventariados foram atualizados: capa em `main.register_parent_gallery_cover_photo` herda a origem; pasta pública/privada em `main.register_folder_photo_asset` usa origem persistida e validada. `pytest tests/test_tenant_producers.py tests/test_gallery_workflow_remediation.py tests/test_private_upload_batches.py -q`: inicialmente **25 passed / 1 failed**, 124,03 s. A fixture de capa enviava campo extra proibido e chave curta, contrariando o contrato existente. Corrigida sem relaxar validação; repetição focada da capa: **1 passed**, 4 deselected, 40,48 s. Assim, os 26 casos passaram em suas respectivas execuções. PostgreSQL cobre herança pública/privada, capa, rejeição/ignorância do tenant externo conforme contrato, e UUID estável no retry. Regressões cobrem upload JPEG, import/lotes e retomada; workers desta versão não criam PhotoAsset. Nenhum insert em lote dessas entidades no produto; nenhuma atribuição implícita de tenant.

### Task 5.0 — interrupção dos escritores

A revisão identificou que o script construía/migrava sem parar todos os workers antigos. Acrescentados delta verificável e task antes da correção. `bash scripts/test_deploy_homolog.sh` pelo Git Bash: **exit 0**, políticas de deploy/limpeza/facial e shell aprovadas. Nova cobertura simula imagens prontas → parada API/general/faciais/ajuste → conferência por labels exclusivos → Alembic. Falha de parada ou escritor ainda ativo cancela migration; Evolution/vizinhos não são alvos. Proteções existentes de schema/rollback e branding mantidas. Jobs não são removidos. Não houve execução do script no servidor.

### Checkpoint integrado — em andamento

Frontend sem mudança de código: `npm ci` (439 pacotes), `npm run lint` (exit 0; 37 avisos preexistentes), `npm test -- --maxWorkers=2` (**50 arquivos / 352 testes aprovados**, 102,02 s), `npm run build` (compilação/TypeScript/22 páginas aprovados) e `npx tsc --noEmit` (exit 0). A primeira execução Vitest sem limite de workers sofreu timeouts/erro de inicialização de sete workers nesta estação de 8 GiB; reexecução com dois workers passou, sem alterar testes/configuração/frontend.

Ruff backend completo aprovado. OpenSpec `validate --strict --all --json` exit 0, incluindo a change sem issues; avisos informativos de arquivo de changes antigas permanecem fora deste escopo. Teste de preservação de branding: 14 casos, 12 aprovados/2 skips (fixture Docker opt-in e privilégio de symlink Windows); política/shell deploy aprovados novamente, incluindo origem pública já correta sem escrita de ambiente.

Os ciclos de downgrade históricos foram vinculados explicitamente a `LEGACY_SCHEMA_HEAD=0068`: assim verificam suas próprias regras sem contornar a barreira de 0069. A cadeia completa/legado e recusa de reversão com propriedade são cobertos pelos ensaios novos. Dois testes históricos usam inserção refletida para as colunas que existem naquela revisão, sem preencher propriedade no produto.

A execução backend Windows ficou lenta e já usava uma versão anterior das fixtures históricas carregadas em memória. Foram interrompidos somente os dois processos de pytest criados nesta task, conferindo PID/comando/diretório temporário exclusivo; não houve interrupção de processos preexistentes. Nenhuma aprovação é atribuída a essa execução interrompida.

A validação completa foi reiniciada em cópia descartável do código atual, Python 3.13.15/Linux, imagem local existente `275bacac0fb3`. Container próprio `pyp-tenant-suite-20260929`, limite 2 CPUs/1 GiB, fonte montada somente-leitura e copiada para seu `/tmp`; arquivos de ambiente reais são excluídos. Compartilha apenas namespace do PostgreSQL sintético próprio `pyp-tenant-test-20260929`; proxy loopback próprio 55469→5432 mantém os guards das fixtures. O servidor Oracle, credenciais reais e outros containers não participam dos testes. Resultado ainda pendente.

A imagem Linux existente precisava das dependências de push acrescentadas desde sua construção; foram instaladas no container descartável a partir dos requirements atuais, sem alterar a imagem original. A coleta inicial incompleta não conta como validação. O primeiro ensaio Linux ainda sofria com I/O de DDL SQLite; foi substituído somente o container próprio por outro com workspace/fixtures em memória temporária (`/dev/shm`, 1 GiB, container limitado a 2 CPUs/2 GiB). A execução em andamento verifica funcionalidade, não desempenho de disco/capacidade de produção. Uma conferência do baseline SHA-256 confirmou **28 arquivos preexistentes sem alteração** no checkout original.

High-res PostgreSQL opcional foi executado em processo separado no mesmo container próprio: **4 passed**, 52,07 s, incluindo concorrência/retomada e ciclo histórico de migration. O assert do head histórico foi reconciliado com 0068 em vez do valor antigo 0057. A validação backend completa passou a usar quatro processos pytest com banco SQLite e todos os roots de storage exclusivos por processo, definidos por plugin temporário fora do Git antes de importar a aplicação. Testes PostgreSQL mantêm schemas/bancos UUID próprios. A instalação temporária de pytest-xdist não altera requirements, imagem original ou CI. O processo serial criado nesta task ficou suspenso para liberar CPU enquanto o conjunto isolado é verificado; resultado integrado ainda pendente.

A primeira execução paralela identificou três regressões (**251 passed / 3 failed**, 132,10 s): join implícito origem/privada ficou ambíguo com a nova FK composta; fixture WhatsApp usava sessão administrativa sem administrador; contador de queries incluía as quatro consultas fixas novas de contexto. Corrigido join explícito com UUID/proprietário, fixtures de WhatsApp/notificações/ajuste com administrador vinculado e preservado o limite anterior das agregações separando apenas o custo fixo de autorização (máximo quatro queries). Não foi relaxada autorização nem integridade. Reexecução focada dos fluxos afetados: **9 passed**, 20,23 s. Suíte integrada reiniciada com todas as correções.

Ensaio remoto somente-leitura de `pg_dump -Fc`: **7,641 s**, 105.192.892 bytes descartados no stream, exit 0. Não foi criado arquivo nem backup, e nenhum byte de conteúdo entrou em logs/relatório. Esse ensaio mede leitura lógica da base atual, não tempo de gravação/restauração/limpeza nem duração garantida da janela.

### Inventário da limpeza — leitura concluída

A tentativa inicial do CLI foi recusada porque o serviço existente usa `APP_ENV=staging`, enquanto a rotina aceita somente homologação. Confirmados destino, mounts exclusivos e domínio, foi aplicado apenas ao processo de leitura o mesmo `APP_ENV=homolog` usado pelo wrapper operacional existente. Nenhum arquivo de ambiente ou configuração persistida foi modificado. `python -m app.homolog_cleanup --mode inventory` aprovou, sem executar descarte.

Dados operacionais atuais: 12 origens, 18 pastas, 3.214 fotos/jobs de mídia, 3.306 jobs faciais, 28.730 embeddings, 19 buscas e 10.941 snapshots, uma cliente, sete sessões de cliente, duas assinaturas push de cliente, 16.487 eventos de cliente/acervo, 126 comentários, 40 seleções, dois pedidos com 40 itens e um grupo de pagamento. Mídia: um source de 9.830.265 bytes e 9.833 derivados somando 1.844.179.782 bytes; history/referências faciais vazios.

Preservados pelo procedimento existente: um admin, 71 sessões administrativas, 18 assinaturas push administrativas, 258 eventos de segurança, dois tokens de ação e oito desafios de segurança; branding, PIX global, sete configurações de notificação, ajuste de prévia, dois presets/cinco tiers, configuração do canal e registros operacionais classificados como preservados. A conexão Evolution continua `open`. Essas são contagens, sem identificadores pessoais/segredos; comparar novamente imediatamente antes/depois da operação autorizada. `tenant`/`tenant_admin` serão acrescentados e preservados após 0069. Nenhum backup remoto foi criado e nenhum dado descartado nesta preparação.

### Reconciliação das regressões integradas

A execução completa alcançou 100% dos 909 casos coletados, mas o resumo final da sessão deixou de estar disponível após interrupção da conversa. Não é atribuída aprovação àquela execução. O cache identificou 40 casos a corrigir/reexecutar: três limites de queries contavam as quatro consultas fixas novas de contexto; uma fixture histórica ainda inseria pelo ORM atual em schema 0068; a fixture compartilhada de upload recriava o admin que o helper de autenticação agora já persistia. Corrigidos os testes mantendo o orçamento anterior das consultas de negócio, propriedade obrigatória e os gates de acesso.

Reexecução dos 40 casos: **33 passed / 7 failed**, 35,95 s. Os sete restantes identificaram que o admin sintético compartilhado precisava manter `email_verified=True`, anteriormente preenchido pela criação duplicada removida. Corrigida a fixture; reexecutados os módulos completos de notificações/configurações/pagamentos, push, lotes privados e entrega de pedidos: **44 passed**, 17,86 s. Não houve mudança de comportamento do produto para acomodar fixtures. Ruff completo e validação estrita da change aprovados novamente. A aprovação integrada final será obtida pela CI do PR em rascunho; abrir/push dessa branch não libera homologação.

### Tasks 5.1 e 5.2 — implementação validada e pacote revisado

Release preparada: **`b4c320e75cbe0d786d8b05d62d57b77aa796a2ec`**, [PR #115](https://github.com/conradodeita/markina-gallery/pull/115), [CI 36586629460](https://github.com/conradodeita/markina-gallery/actions/runs/36586629460), concluída com sucesso em 2026-09-29 por volta de 15:08 UTC. O job de deploy foi **skipped**, conforme gatilho restrito a push em develop; não houve publicação.

- Backend Python 3.13/Linux: **890 passed / 19 skipped**, 550,55 s. Ruff aprovado. PostgreSQL 17 sintético configurado na CI executou a fundação nova. Os skips são condicionais de suítes anteriores que exigem outros bancos PostgreSQL dedicados, concorrência/locks específicos e o caso SQLite de limpeza (não suportado); não são falhas ignoradas. Os quatro casos high-res PostgreSQL condicionais já passaram em execução local separada documentada acima. Não se atribui aprovação PostgreSQL às demais variantes puladas.
- Frontend: **50 arquivos / 352 testes aprovados**, lint e build aprovados. Permanecem avisos preexistentes de lint/depreciação; TypeScript local também aprovado. Nenhuma alteração de frontend integra a release.
- Branding: 14 testes, **13 aprovados / um skip** da fixture Docker opt-in na CI Linux. Políticas de deploy/manutenção/facial e testes shell aprovados.
- OpenSpec estrito completo e gitleaks do histórico completo aprovados na CI. A change foi validada localmente novamente sem issues.

Revisados modelo/FKs, migration e barreira de downgrade, pontos de autenticação/publicação/remoção, produtores e alterações mecânicas das fixtures. Conferência SHA-256: **28 arquivos preexistentes do checkout original preservados**. Os 96 arquivos da implementação contêm somente a change; nenhum `.env`, banco, dump, log, chave ou artefato temporário foi incluído. O procedimento operacional e o registro final de evidências são documentação complementar, sem mudança de código operacional sobre b4c320e.

Containers locais exclusivos de suíte e PostgreSQL sintético foram parados após os ensaios; o container descartável da suíte foi removido por seu próprio `--rm`. Nenhum container preexistente foi parado. O cache final dos testes reexecutados ficou sem falhas. Logs/XML temporários ficam fora do Git em `C:/codex-data/test-runs/`.

**Bloqueio operacional real:** tasks 6.2–6.5 aguardam aprovação específica da release, janela remota/aceite e revisão humana. O descarte de negócio já está autorizado, mas o deploy não foi executado. Não há tarefa local independente restante nesta change. Specs principais e arquivo permanecem intocados até revisão humana.

### Reconciliação documental pós-publicação — 2026-09-30

O parágrafo anterior descreve o estado em que o PR #115 ainda era rascunho; deixou de ser o estado atual. O PR foi integrado no merge `ff680e411d0c04fd3ca82c1885204891f56451a9` em 2026-09-29 20:41 UTC. O [workflow 36628097734](https://github.com/conradodeita/markina-gallery/actions/runs/36628097734) aprovou backend, frontend, gitleaks, OpenSpec e `deploy-homolog`, encerrando às 20:53 UTC. O log registra escritores próprios interrompidos, backup lógico da Markina, migration `20260929_0069 (head) → 20260929_0069 (head)`, serviços saudáveis, topologia `markina-gallery` / `127.0.0.1:8080` / `markina-homolog.duckdns.org` e inventário posterior com `tenant=1`, `tenant_admin=1`, `admin_user=1`, `client=0`, `photo_asset=0` e quatro raízes de mídia vazias. O [inventário anterior de 19:34 UTC](../2026-09-29-fix-homologation-service-resume/validation.md) já encontrava a revisão 0069 aplicada; portanto o workflow de merge não prova a aplicação inicial de 0068 para 0069.

O ensaio remoto posterior da change `fix-homologation-service-resume` confirmou checkout no SHA esperado, schema 0069, serviços Markina e Evolution ativos, Firefly/Proxy Manager/Portainer ativos e quatro healthchecks HTTP 200. O [workflow 36747828201](https://github.com/conradodeita/markina-gallery/actions/runs/36747828201) publicou depois `ce628f01d4aa9f7f9d7eb24bf347e30ae42579d3`, manteve 0069 e passou nos healthchecks. O registro legível da entrega e das lacunas está em [deploy-2026-09-29-tenant-foundation.md](deploy-2026-09-29-tenant-foundation.md).

Validação documental desta reconciliação: `npx -y @fission-ai/openspec@latest validate add-tenant-ownership-foundation --type change --strict --no-interactive` e `git diff --check` aprovaram. A task 6.4 foi marcada concluída; 6.2 e 6.3 permanecem pendentes pelos pontos individualizados no registro, e 6.5 aguarda revisão humana. Nenhum deploy, limpeza, migration ou alteração de ambiente foi executado nesta reconciliação.

### Complemento de aceite remoto — 2026-09-30

O texto acima registra a reconciliação documental anterior, não o estado final deste complemento. O histórico restrito `/var/lib/markina-gallery/deploy-state/history.log` mostra `previous 04c6bb98...` e `last-healthy b4c320e7...` às 16:50:05 UTC de 2026-09-29. O manifesto restrito do dump `predeploy-20260929T164414Z-b4c320e75cbe.dump` identifica a mesma origem e alvo, criado às 16:44:22 UTC, com 105.192.965 bytes; `pg_restore --list` dentro do container PostgreSQL próprio aprovou. Isso associa backup e primeira publicação, mas não reconstitui a ordem exata da migration/limpeza ou um ensaio de restauração. A task 6.2 permanece aberta.

O [workflow 36753375829](https://github.com/conradodeita/markina-gallery/actions/runs/36753375829) publicou `af4873a3f52c7dc1ad1b2d0fcf8776e55becfd2a` em homologação com cinco jobs aprovados. Leitura em 2026-09-30 19:18:25 UTC: checkout nesse SHA, `alembic current = 20260929_0069 (head)`. `docker ps` encontrou os serviços Markina API/web/workers/DB/Redis/Evolution saudáveis, nginx próprio em `127.0.0.1:8080`; Firefly, Proxy Manager e Portainer permaneceram ativos. Nenhum container ou rede vizinha foi alterado neste aceite.

Com o proprietário autenticado no painel por senha/TOTP, foi criada uma Galeria pública temporária e enviada uma imagem abstrata JPEG sintética. A prévia administrativa protegida abriu. O proprietário entrou como cliente via OTP no WhatsApp previamente autorizado; a galeria e sua prévia protegida abriram. Nessa sessão, foi selecionada uma foto, visualizado o carrinho e finalizada a seleção sem cobrança. O histórico exibiu uma seleção finalizada com um item. Nenhum pagamento PIX foi iniciado. A exclusão da galeria, confirmada pelo proprietário, concluiu 100% e a lista administrativa ficou vazia.

Inventário posterior por `python -m app.homolog_cleanup --mode inventory` com `APP_ENV=homolog` apenas no processo: `tenant=1`, `tenant_admin=1`, `admin_user=1`, `client=1`, `photo_asset=0`, `sale_order=1`, `sale_order_item=1`, `parent_gallery=2` (tombstones), quatro raízes de mídia com zero arquivos. Consulta SQL somente-leitura da galeria temporária confirmou `lifecycle_status=deleted`, `tenant_id` igual ao vínculo administrativo ativo, uma conta ativa, uma foto removida e pedido congelado `not_required` de zero centavos; a referência direta ao arquivo foi anulada. As constraints FK compostas verificadas nos testes impedem foto de proprietário divergente enquanto existe. Não foi coletada consulta de `tenant_id` da foto antes da exclusão, portanto não se afirma essa medição direta remota.

A tela de Clientes mostrou uma identidade de teste sem galerias, com um pedido e estado `Histórico comercial preservado`, sem botão de exclusão. O inventário inclui ainda registros operacionais de ensaios anteriores, incluindo webhook receipts e auditoria; a limpeza global removeria mais que o ensaio atual. Nenhum TRUNCATE, alteração de ambiente/segredo ou envio adicional foi executado. O cadastro e pedido de teste ficam pendentes de procedimento específico compatível com a proteção de histórico comercial. O escopo validado da task 6.3 é checkout sem cobrança, não cobrança PIX.

### Fechamento e publicação do registro — 2026-09-30

O [PR #131](https://github.com/conradodeita/markina-gallery/pull/131), aprovado pelo proprietário, integrou a documentação do aceite no merge `b4c7f08f867bd024c0a57e21288517c9de924595`. O [workflow 36772380840](https://github.com/conradodeita/markina-gallery/actions/runs/36772380840) concluiu backend, frontend, OpenSpec, gitleaks e `deploy-homolog` com sucesso às 20:44:50 UTC. O deploy criou backup lógico exclusivo da Markina, interrompeu escritores próprios e conservou a revision `20260929_0069 (head)`. Às 21:01 UTC, checkout remoto no merge, serviços próprios saudáveis, Evolution saudável, Firefly/Proxy Manager/Portainer ativos e `/healthz` e `/api/health` públicos HTTP 200. Inventário sanitizado posterior: `tenant=1`, `admin_user=1`, `whatsapp_channel_settings=1`, `client=1`, `sale_order=1`, `photo_asset=0`, `parent_gallery=2` e source/derivatives vazios. Nenhuma limpeza global foi executada.

Em leitura posterior, `tenant.created_at = 2026-09-29T16:45:39.908057+00:00`, depois do manifesto do backup pareado de 16:44:22 UTC e antes do `last-healthy b4c320e7` de 16:50:05 UTC. Esses marcos estreitam a janela da primeira migration, mas não demonstram a ordem completa dos comandos ou autorização específica anterior. A task 6.2 permanece desmarcada. O proprietário revisou o resultado e aprovou sincronizar os oito requisitos das três delta specs e arquivar a change com essa pendência explícita. `openspec validate --specs` aprovou 16 specs, a comparação dos oito blocos da delta com as specs principais foi exata e a validação estrita da change aprovou antes do arquivo.

### Limpeza operacional autorizada após o arquivo — 2026-09-30

O [PR #132](https://github.com/conradodeita/markina-gallery/pull/132) publicou a sincronização e o arquivo no merge `8a90764f2790f6520b06903ff55cf03e78d2f8ea`. O [workflow 36783553625](https://github.com/conradodeita/markina-gallery/actions/runs/36783553625) aprovou os cinco jobs, inclusive deploy. O proprietário informou CI verde e foi retomada a limpeza abrangente já autorizada na conversa: os dados do servidor de homologação podem ser descartados, preservando admin, acesso e Evolution. Essa autorização abrange os registros operacionais anteriores ao último ensaio; a operação não foi limitada à exclusão daquele cadastro pela interface comercial.

Destino conferido: `/opt/markina-gallery`, checkout limpo no merge acima, projeto Compose `markina-gallery`, arquivo `docker/docker-compose.yml`, override persistente de branding e perfil de ajuste de prévias já ativos. Nginx próprio em `127.0.0.1:8080`, origem pública `https://markina-homolog.duckdns.org`; nenhum proxy, porta, certificado, DNS, rede ou volume de terceiros foi alterado. Foram parados somente API, worker, os três workers faciais e o worker de ajuste de prévias. DB, Redis próprio e os três serviços Evolution permaneceram ativos. Não foi alterado `.env`, segredo, flag facial, código ou schema. A indisponibilidade da aplicação durante a operação havia sido permitida pelo proprietário; não foi medida sua duração exata.

Backup exclusivo da Markina criado após a parada dos escritores em 22:41:15 UTC: `/var/lib/markina-gallery/backups/preclean-20260930T224115Z-8a90764f2790.dump`, **395.115 bytes**, SHA-256 `98461dc0ce87002fef7bb3ec854fa0f52cade598c0e275d2e6e0610688ed9ff3`, arquivo/manifesto com modo 0600. `pg_restore --list` no PostgreSQL próprio aprovou a leitura estrutural; não foi executada restauração. O dump restrito permanece para recuperação e contém o estado anterior à limpeza.

O inventário imediatamente anterior contabilizou um cliente/telefone/sessão, duas galerias tombstone, um pedido sem cobrança e seu item, 117 webhook receipts, 197 eventos de auditoria operacionais e os demais resíduos de OTP/notificações/lifecycle. As quatro raízes de mídia já estavam vazias. Foi executado uma vez o CLI versionado `app.homolog_cleanup`, com `APP_ENV=homolog` somente no processo, modo `execute` e confirmação literal `DELETE_HOMOLOG_GALLERIES_AND_CLIENTS`. Sua classificação fechada de schema e `TRUNCATE ... RESTRICT` preservaram as tabelas administrativas/configurações; também foram removidos sessões/push de cliente e auditoria operacional segundo a política existente. Em seguida foi aplicado `FLUSHDB` **somente ao serviço Redis da Markina**, sem tocar o Redis da Evolution.

Verificação antes e depois da retomada: **todas as contagens operacionais e arquivos/bytes das quatro raízes ficaram em zero**; o conjunto completo de contagens preservadas permaneceu igual. Entre os preservados: `admin_user=1`, `tenant=1`, `tenant_admin=1`, 87 sessões administrativas, 20 assinaturas push administrativas, 311 eventos de segurança, nove desafios de segurança, dois tokens de ação, branding/PIX globais e configuração do canal. A conta e o pedido sintéticos deixaram de ser pendência de limpeza. Essa operação excepcional de homologação não muda a proteção comercial da interface.

Os serviços próprios foram retomados no mesmo SHA e o Nginx próprio recriado. API/web/worker/Nginx, ajuste de prévias, os três workers faciais, DB/Redis e Evolution ficaram saudáveis; os healthchecks `/healthz` e `/api/health`, locais e públicos, aprovaram. Firefly, Nginx Proxy Manager e Portainer continuaram ativos. Consulta somente-leitura pelo adaptador configurado da Evolution confirmou `state=open` e identidade conectada presente, sem expor telefone/credencial e sem enviar mensagens ou modificar pareamento.

Evidência sanitizada persistida no servidor em `/var/lib/markina-gallery/backups/homolog-cleanup-20260930T224115Z-8a90764f2790.manifest.txt`, registrada às 22:46:28 UTC e complementada com o estado de conexão. Contém inventários de contagem antes/depois, hash do backup e resultados das verificações, sem PII ou segredos. A task **6.2 permanece aberta**: a limpeza atual não reconstitui autorização, janela ou sequência da primeira aplicação da migration 0069.

Validação do complemento documental: `npx -y @fission-ai/openspec@latest validate --specs --strict --no-interactive` aprovou as 16 specs principais; `git diff --check` aprovou. O diff contém somente este registro, a reconciliação da pendência de limpeza no relatório e nas notas de tasks, sem código, delta spec, alteração de checklist ou arquivo sensível.
