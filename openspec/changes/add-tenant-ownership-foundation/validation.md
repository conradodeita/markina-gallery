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
