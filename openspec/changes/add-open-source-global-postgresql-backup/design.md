# Design

## Context

Consulte `proposal.md` e os deltas desta change para motivação e contratos. O PostgreSQL contém o estado global e registros de todos os fotógrafos; os bytes de mídia ficam em armazenamentos próprios. A tentativa antiga via Google Workspace foi aposentada e não fornece runtime, credenciais ou mecanismo reutilizável.

A evidência disponível está em [`validation-results.md` da PR #438](https://github.com/conradodeita/markina-gallery/blob/551e28b6717f5e811c3cabef2ad5ccfeb114328f/openspec/changes/prove-open-source-backup-and-recovery/validation-results.md), no SHA `551e28b6717f5e811c3cabef2ad5ccfeb114328f`. O ensaio usou dados sintéticos, PostgreSQL 17.11, Restic 0.20.0 e Rclone 1.76.0, com destino Rclone local. `pg_dump` em formato custom foi cifrado, lido e restaurado em banco separado; hash e contagens das entidades sintéticas conferiram. O tempo total medido foi 5,29 s nesse conjunto pequeno, não uma medida de RPO/RTO de produção. A extração seletiva cobriu apenas parte da árvore de negócio; não prova recuperação completa por fotógrafo. A prova de mídia foi separada e local (`crypt → local`), sem destino, conta ou conteúdo real.

### Evidência de configuração PostgreSQL e bootstrap — revisão estática de 26/11/2026

- `docker/docker-compose.yml:213-222` declara o serviço principal `db` com imagem `postgres:17-alpine`, base e usuário vindos de `POSTGRES_DB`/`POSTGRES_USER`, conexão das aplicações por `DATABASE_URL` e volume `pgdata`. A tag fixa a major 17, mas não fixa patch/digest. A instância Evolution usa serviço, base e volume separados e não integra o banco Pick-your-Pic.
- `.github/workflows/ci.yml:218-249` usa `docker.io/library/postgres:17-alpine` em serviços PostgreSQL sintéticos. Isso confirma a major exercitada em CI, não a imagem atualmente carregada em produção.
- A revisão de `backend/migrations/versions`, `backend/migrations/env.py`, `backend/app` e Compose não encontrou DDL explícito de extensão ou role para a aplicação. Os parâmetros de usuário/base vêm do ambiente Compose; os atributos efetivos do role e a existência de objetos globais do cluster não são demonstrados pelo repositório. A única criação explícita de role localizada foi fixture de teste em `backend/tests/test_capacity_observability_postgres.py`.
- `scripts/deploy-prod-app-services.sh:19,46-47` fixa a revisão de schema esperada pelo fluxo de API/web como `20261113_0126`; isso é um contrato do código de release, não uma leitura da revisão real do servidor. A revisão atual, patch/digest da imagem, extensões ou roles do runtime não foram consultados.
- Os utilitários versionados de release usam `pg_dump -Fc --no-owner --no-privileges`; alguns verificam `pg_restore --list`, e `scripts/orders_pilot_release.py:790-810` restaura um archive em PostgreSQL temporário para ensaio de migration. Não encontrei neles Restic/Rclone nem uma recuperação global durante indisponibilidade. Esses ensaios não comprovam globals de cluster, roles/grants, extensões instaladas ou cobertura de todas as tabelas/relacionamentos do banco atual.

### Evidência do caminho protegido de recuperação — revisão estática de 26/11/2026

`.github/workflows/production-app-handoff-recovery.yml` oferece `workflow_dispatch`, confere CI do SHA exato, passa por `production-preflight` para inventário SSH e exige o environment `production` separado para `recover`, comparando fingerprint e vínculo do destino. Isso é um canal de controle independente da UI/DB do SaaS quando GitHub Actions, aprovação do environment, configuração protegida e conectividade SSH estão disponíveis; nenhum desses requisitos foi testado nesta leitura.

O modo existente `handoff-recover` em `scripts/deploy-prod-app-services.sh` recupera checkout/serviços API e web. Ele chama `database_revision()` via `docker compose exec ... api ... alembic current` e depois verifica runtime e HTTPS; não executa `pg_restore`, Restic ou Rclone e depende de o banco responder para concluir suas próprias verificações. Já `restore-support` em `.github/workflows/production-app-compose-bridge-install.yml` e `scripts/install-prod-app-compose-bridge.sh` restaura somente os artefatos do suporte operacional protegido; os demais modos cuidam do runtime legado aposentado. Nenhum deles restaura o PostgreSQL.

Conclusão limitada: o canal protegido existente é uma base possível para um futuro modo fixo de bootstrap de banco, mas hoje não existe operação allowlisted que localize um snapshot Restic, acesse configuração/chave do destino e restaure o banco isoladamente. Não reutilizar `restore-support`, `retire-backup-runtime`, workflows antigos de Google Workspace nem SSH ad hoc. Um novo modo protegido, sua identidade/chave de leitura, alvo isolado, aprovação e rollback ainda precisam de desenho revisado; o estado deste contrato não permite declarar a task 1.4 concluída.

### Plano de cobertura sintética PostgreSQL — task 1.1, ainda não executado

O ensaio futuro SHALL usar somente dados sintéticos e dois alvos PostgreSQL descartáveis e isolados: origem e destino de restauração, sem volumes persistentes compartilhados. Ambos devem usar a mesma major suportada pelo projeto; a tag atual `17-alpine` não fixa patch/digest e não prova a imagem do runtime. A imagem exata e a política de pin serão confirmadas antes de declarar compatibilidade.

Na origem, aplicar a cadeia Alembic até o head da fixture e semear dois fotógrafos/tenants sintéticos com relações e registros que percorram todas as tabelas ativas da aplicação, incluindo referências de mídia/arquivo frio e registros financeiros sintéticos sem executar operações externas. Antes do dump, capturar inventário determinístico de schemas e objetos não sistêmicos: tabelas comuns, particionadas e foreign tables; views/materialized views; sequências e estado das sequências; large objects caso existam; constraints, índices, triggers, funções/procedures, tipos, regras, políticas RLS e o head Alembic. Comparar também contagem e hash determinístico de linhas da fixture por tabela e tenant, ordenadas por chave estável; não registrar valores pessoais, apenas os dados artificiais do ensaio.

Inventariar separadamente `pg_extension` (nome e versão) e roles globais (atributos sem segredo, memberships, owners, grants e default privileges). A fixture deve criar roles sintéticas `NOLOGIN`, sem senha, e privilégios mínimos representativos; não reutilizar nomes nem credenciais do runtime. A restauração deve provisionar extensões/roles sintéticas no destino antes do archive quando necessário, comparar o inventário e demonstrar exatamente quais owners/ACLs sobrevivem ao dump usado. Os comandos de release observados usam `pg_dump -Fc --no-owner --no-privileges`: esse perfil não preserva ownership nem ACL. `pg_dump` também não transporta roles globais ou tablespaces do cluster. Portanto, a prova SHALL identificar a diferença, sem alegar restauração completa de roles/grants; o mecanismo final (provisionamento declarativo revisado ou mudança do contrato do dump e provisionamento prévio) permanece decisão aberta.

Gerar archive custom-format com os flags exatos candidatos da implementação, registrar tamanho e SHA-256, exigir `pg_restore --list` bem-sucedido e restaurar em banco vazio distinto com `pg_restore --exit-on-error`, depois de preparar apenas extensões/roles sintéticas explicitamente declaradas. Validar que o restore não compartilha volume, porta publicada, `DATABASE_URL`, API ou worker da origem. Comparar inventário de relações/definições, linhas e hashes por tabela/tenant, sequências, constraints/índices/triggers/views/funções, RLS e head Alembic. Comparar extensões por nome/versão e roles/memberships/grants contra o manifesto sintético de bootstrap, anotando os itens que o archive não cobre.

Casos negativos obrigatórios do plano: archive truncado ou SHA divergente, versão incompatível, extensão ausente/versão errada, role esperada ausente, `pg_restore` parcial/falho e divergência de objeto, sequência ou conteúdo. Qualquer caso desses invalida o resultado: não pode produzir status de sucesso, promover destino nem autorizar prune. O ensaio é lógico e limitado ao fixture; não demonstra patch/digest, roles, extensões ou volumes reais, recuperação de host/cluster, arquivos de configuração/secrets, Redis/filas, bytes de mídia ou estado de serviços. Hashes/contagens sintéticos não substituem ensaio com inventário runtime autorizado. A task 1.1 permanece aberta até a fixture rodar e as decisões de cobertura de globals/ACL serem registradas.

### Procedimento candidato de bootstrap protegido — task 1.4, ainda não aprovado nem executado

O canal em consideração é uma operação fixa em GitHub Actions, sem interface adicional ao fotógrafo e sem depender da UI/API do SaaS. Para o cenário limitado em que PostgreSQL está indisponível, mas host, rede e canal protegido continuam alcançáveis: aceitar somente SHA de `main` com CI exigida verde; usar inputs enumerados/validados para uma referência de snapshot existente; executar preflight protegido somente de leitura; vincular a operação ao inventário/fingerprint exatos do alvo; e exigir a aprovação separada do environment `production`. A operação deve usar helper versionado e allowlist, lock exclusivo, conexão já vinculada e saída sanitizada. Não aceitar comando, caminho, remote, ID de container, imagem ou variável de conexão arbitrários, nem usar SSH ad hoc.

O helper deverá restaurar exclusivamente para um alvo PostgreSQL novo, isolado e identificável por esta execução: sem porta pública, sem conexão de aplicação, sem API/worker e sem reutilizar volume ativo. O destino terá versão/major e extensões verificadas. O processo deverá verificar repositório e snapshot selecionados, restaurar para staging restrito o archive completo daquela cópia (permitindo ao Restic autenticar/verificar cada blob lido), calcular e comparar SHA-256 com o manifesto de integridade definido pela implementação, validar `pg_restore --list`, executar `pg_restore --exit-on-error` e aplicar os checks de relações, dados sintéticos/fixture, roles, grants, extensões e schema da task 1.1. Gerar recibo sanitizado com referência do snapshot, SHA do archive, identidade do alvo, tempos e resultados, sem conteúdo do banco nem segredos. Nenhum sucesso poderá ser mostrado se a verificação ficar ausente, incompleta ou incerta. Uma verificação integral de todos os packs do repositório Restic é distinta da integridade do snapshot restaurado e não será presumida como parte deste fluxo sem decisão explícita de escopo/custo.

Falha antes ou durante o restore mantém a base ativa intocada. Preservar snapshot, material de recuperação e recibo/diagnóstico sanitizado; não substituir a origem, não iniciar workers e não remover recursos cujo vínculo à execução não possa ser provado. Limpeza só poderá alcançar o alvo temporário criado pela mesma execução após verificar sua identidade e estado; se a propriedade/resultado forem incertos, preservar o alvo e exigir reconciliação protegida. Qualquer promoção para produção fica fora deste procedimento e exige operação/change, inventário e autorização próprios, snapshot recuperável da instância anterior, compatibilidade de schema/versões, plano de cutover e rollback verificado. O rollback do ensaio isolado é abandonar esse alvo preservando evidências; não é restaurar sobre o banco ativo.

Este canal não resolve todos os cenários de desastre. Se a UI/API estiver indisponível, um operador autorizado ainda pode iniciar o fluxo protegido, desde que GitHub Actions, aprovação, host, rede, configuração do destino e chave estejam acessíveis. Se o host/volume local também se perdeu ou está inacessível, o workflow SSH existente não consegue executar restore nesse host; a configuração/chave guardada somente nele tampouco pode ser recuperada. Sem destino externo legível, cópia da chave fora do host e procedimento aprovado para provisionar um host substituto, a recuperação é impossível. Se GitHub Actions/environment, SSH ou a identidade de leitura falhar, este desenho também não oferece outro canal. Esses limites precisam estar visíveis na UI/recibos e no runbook; não alegar recuperação autônoma completa.

Permanecem escolhas de segurança/produto para o proprietário: estender o workflow de handoff ou criar um workflow protegido dedicado; quem pode disparar/aprovar e se há controle dual; onde residem config Rclone e senha Restic e qual custódia off-host permite recuperar perda total do host; como prover roles/ACL/extensions sem incluir credenciais; quota/capacidade, retenção e limpeza de alvos isolados; e quais evidências/autorização serão exigidas antes da promoção e rollback do banco ativo. Até essas decisões e um ensaio protegido revisável, 1.4 permanece aberta e nenhuma operação está autorizada por este documento.

## Goals / Non-Goals

**Goals:**

- Usar Restic e Rclone como ferramentas maduras para um repositório global cifrado, com comandos e escopos fixos integrados ao backend/worker existente.
- Manter a operação normal em `/admin/platform`, protegida pela identidade do proprietário, reautenticação e auditoria existentes.
- Separar cópia global do PostgreSQL, arquivo frio de mídia, volumes de fotos, configuração do host e segredo de cifragem.
- Tornar uma recuperação global verificável em alvo isolado e deixar a promoção do banco ativo para um gate operacional próprio.
- Preservar as referências por objeto: objetos Drive já existentes ficam no Drive sem migração automática; novos objetos Rclone de mídia carregam identidade explícita do provider, conforme decisão do proprietário e coordenação com a change #441.

**Non-Goals:**

- Implementar uma engine própria, uma UI pública/administrativa paralela do Backrest, backup de bytes de fotos ou recuperação seletiva de um fotógrafo.
- Migrar objetos Drive, trocar o provider de objetos existentes, executar recuperação fria de mídia ou alterar fila, catálogo, cobrança e ledger do Tenant.
- Copiar `.env`, arquivos de sistema, imagens/volumes Docker, Redis ou outros serviços para dentro do repositório PostgreSQL.
- Instalar ferramentas, configurar destino/credenciais, aplicar migration, despachar workflow ou operar em produção nesta change documental.

## Decisions

### Restic para snapshots e cifragem; Rclone como transporte

O serviço SHALL usar ferramentas oficiais pinadas e invocadas por uma interface fixa do servidor. Restic entrega repositório cifrado e verificação; Rclone transporta esse repositório ao destino escolhido. A prova sintética já exercitou essa composição sobre storage local. Uma engine própria aumentaria código de criptografia, formato, concorrência e recuperação sem benefício demonstrado. Backrest pode ser avaliado para monitoramento interno, mas não é dependência nem interface de operação do SaaS; sua UI/API não será exposta, sua configuração não será editada diretamente e a autenticação não será desabilitada para contornar limites de API.

### Backup lógico da base global e destino isolado

O primeiro caminho implementável será um dump consistente da base de aplicação inteira, restaurado para uma base isolada. `pg_dump` em formato custom foi o caminho provado. A task de implementação deverá confirmar a versão major suportada, extensões, ownership/roles e a forma de recriá-los a partir da configuração segura do runtime; o ensaio atual não comprova esses aspectos do cluster. Não haverá dump separado por tenant nesta change.

O dump contém tudo o que estiver persistido na base, inclusive dados sensíveis e referências de mídia; a cifragem protege o repositório, não substitui controle de acesso ou política de retenção. Dados apagados da base podem continuar em snapshots anteriores até sua expiração aprovada. Nenhuma chave ou credencial de destino será registrada em banco comum, Git, frontend, recibo ou log.

### UI SaaS como painel normal; execução por operações fechadas

`/admin/platform` permanece a interface principal para status, ações e configuração não secreta da política aprovada. A página lê o último estado persistido e distingue `unknown`, `unavailable` e `stale`; um GET não executa `rclone`, consulta o destino ou inicia cópia. Ações autenticadas delegam somente operações fixas ao backend/worker, com reautenticação e evento de auditoria. Cadência/retenção só podem ser escolhidas entre políticas aprovadas; destino e material de segredo são provisionados por configuração privada protegida, nunca por campo da UI. Nenhum formulário aceita remote, executável, caminho, opção ou segredo arbitrário.

Quando o SaaS ou seu PostgreSQL estiver indisponível, sua própria UI não pode ser o bootstrap de recuperação. A leitura estática encontrou um canal GitHub Actions com gates `production-preflight`/`production` e SSH fixo, mas nenhum modo atual restaura PostgreSQL. Antes de operação real, deve ser definida e aprovada uma operação allowlisted nesse control plane (ou workflow protegido próprio), com acesso de leitura ao repositório Restic, chave recuperável, alvo isolado, validação e rollback, sem criar segunda UI nem assumir SSH ad hoc. A etapa existente de handoff API/web verifica a revisão do banco e HTTPS e, portanto, não serve como restauração quando o DB está fora.

### Recuperação primeiro isolada; promoção como operação separada

A UI poderá solicitar recuperação para um alvo isolado e apresentar cópia de origem, estado, verificação e versão do schema. O primeiro ensaio não troca o banco ativo. Antes de produção, o fluxo exige inventário atual, compatibilidade de aplicação/schema, plano de impacto zero e rollback preservando a base saudável anterior, além de autorização operacional específica. Uma cópia validada não é por si só autorização para restaurar sobre produção.

O Redis/fila não faz parte desta cópia. Após restauração do PostgreSQL, workers permanecem sem processar operações até que o estado das filas e das operações duráveis seja reconciliado. Em particular, restaurar registros `media_archive_*` não pode repetir cobrança, recuperar mídia, excluir objetos, converter provider ou iniciar uma migração. A implementação deve preservar os IDs de provider por objeto presentes no schema então vigente e apresentar divergências para reconciliação explícita.

### Agenda diária e retenção sem remoção automática enquanto pendente

A cadência diária continua como direção do roadmap. A regra exata de retenção não está fechada para a implementação nova: o histórico registra 7 diários/4 semanais/3 mensais, e há orientação posterior de descartar a cópia anterior somente depois que a mais recente for validada. Até o proprietário reconciliar essas regras para Restic, o sistema mantém ao menos a cópia validada mais recente e não executa prune/expiração automática. A tarefa de retenção não pode ser marcada como concluída por apenas configurar valores no engine.

### Separação por objeto entre Drive e Rclone para mídia

Por decisão do proprietário, objetos já arquivados no Drive permanecem no Drive e não são migrados; novos objetos Rclone recebem identidade explícita do provider. O backup/restauração global PostgreSQL deve preservar `provider_id` e bindings duráveis com escopo de tenant de forma coerente entre o catálogo e o manifesto v2. O roundtrip deve manter cada associação Drive/Rclone, sem inferência por caminho, fallback para provider padrão ou migração automática.

O archive PostgreSQL recupera somente o estado durável gravado no banco, como catálogo, `provider_id` e bindings de tenant que façam parte do contrato persistido. Ele não recupera nem prova a identidade externa da conta/raiz, autorização atual, tokens, configuração Rclone ou chaves. Esses elementos precisam de provisionamento seguro e validação independente sob a mesma conta verificada e a mesma raiz escolhida. A proposta do Executor B registra que V1 não persiste essa identidade e falha fechado até existir uma associação autoritativa; não presumir que o restore pode reconstruí-la de `remote_object_id`, nem preencher a lacuna com credenciais ou valores padrão.

A prova sintética planejada SHALL semear pelo menos dois tenants, cada um com registros de mídia associados a providers distintos (incluindo identidades Drive e Rclone conforme o contrato aprovado), referências e manifesto v2. Depois de dump e restore para DB isolado, comparar por tenant o `provider_id`, binding autoritativo, ID do objeto e referências do manifesto, confirmando que nenhum objeto mudou de provider nem cruzou tenant. Incluir binding ausente, ambíguo ou incompatível; a recuperação deve preservar a referência como não resolvida/falha fechada e não tentar acesso ao provider, fallback ou migração. É prova local com identidades sintéticas; não lê nem grava Drive/Rclone externos.

A change #441 é de titularidade do Executor B e define o contrato do provider de arquivo frio. Esta change global apenas fixa o requisito de roundtrip no banco e permanece dependente da aprovação/implementação daquele contrato; não altera os artefatos de B nem declara concluída a compatibilidade até o teste sintético efetivamente passar.

## Risks / Trade-offs

- [Perda do host junto com a chave] → guardar destino e material de recuperação de chave em domínio independente, definido e verificado antes do uso real.
- [Backup de dados pessoais e registros apagados] → restringir acesso, cifrar, auditar leituras/ações e aprovar uma política de retenção que considere obrigações de exclusão; não remover por conta própria snapshots anteriores.
- [Dump válido sem restauração funcional] → validar restauração isolada, versão PostgreSQL, extensões, roles e schema; reportar RPO/RTO como desconhecidos até medi-los em ensaio representativo.
- [UI indisponível durante desastre] → definir o procedimento de bootstrap protegido antes de ativar operação real, sem publicar um segundo painel.
- [Banco recuperado diverge de mídia/fila atuais] → não processar fila ao iniciar o alvo, comparar estado durável e identities de provider, e reconciliar antes de reabrir workers.
- [Restic/Rclone mudam sem compatibilidade] → pin de versões/fontes, inventário de licença/origem e testes de backup, check, readback e restore antes de atualização.
- [Retenção causa exclusão irrecuperável ou acumula cópias sem limite] → não ativar prune antes da decisão de política e do teste que protege a última cópia validada.

## Migration Plan

Esta change não faz migration nem instalação. A sequência planejada é: (1) revisão humana dos contratos e decisões abertas; (2) implementação local e validação sintética/CI; (3) revisão e integração por PR; (4) inventário protegido de destino, chaves, versão, serviços, schema e rollback; (5) autorização operacional específica antes de configurar ou ativar em produção. A primeira restauração de integração ocorre em base isolada. Qualquer promoção futura preserva a instância saudável anterior e só prossegue com compatibilidade e autorização do proprietário.

O fluxo antigo de Google Workspace, seus módulos, tokens, Picker, chave e workflow não será reinstalado nem reutilizado. Arquivos de mídia do Drive não são movidos por esta mudança.

## Open Questions

As decisões abaixo são gates, não defaults implícitos. As tasks de código dependentes permanecem bloqueadas até que cada resposta esteja registrada; o restante independente pode avançar localmente:

1. Qual destino externo e qual conta/identidade de serviço receberão o repositório Restic? Quais limites de acesso, região, custo e disponibilidade são aceitáveis?
2. Onde fica a chave/senha Restic, como obter cópia de recuperação fora do host e quem controla a custódia? Como revogar/rotacionar credenciais Rclone sem perder leitura do histórico?
3. Para a nova implementação, o proprietário confirma retenção somente do último diário validado ou mantém 7 diários/4 semanais/3 mensais? Como a política trata dados apagados e snapshots antigos?
4. RPO de 24 h e RTO de 8 h permanecem metas desejadas, ou devem ser alterados? Esses valores históricos não foram medidos e não são SLA.
5. O workflow `production-app-handoff-recovery` é um control plane independente da UI, mas hoje recupera API/web e consulta o schema do DB; deve receber uma operação fixa de recuperação PostgreSQL ou haverá workflow protegido próprio? Quem pode iniciá-la/aprová-la, é necessário controle dual, e como o bootstrap continua funcionando quando a API/DB não responde?
6. Qual fonte segura, fora do host, guarda cópia recuperável da senha Restic e configuração/credencial Rclone para perda total do host; quem são os custodiantes autorizados e como revogação/rotação preserva leitura dos snapshots?
7. Como a restauração isolada provisiona extensões, roles e ACLs sem secrets no archive? O perfil existente `--no-owner --no-privileges` será mantido com bootstrap declarativo revisado, ou outro perfil de dump será especificado? Quais identidades sintéticas e grants mínimos cobrem a prova?
8. Qual limite de capacidade/vida útil para o alvo temporário isolado, política de preservação/limpeza após sucesso ou falha e critério para reconhecer recursos incertos sem apagar volumes alheios?
9. A mudança inicial fica restrita a preparar/verificar restore isolado, ou qual change futura poderá promover o DB ativo? Quais inventário, aprovação, snapshot anterior e critérios de compatibilidade/rollback serão exigidos? Qual escopo de desastre (DB indisponível com host acessível versus perda de host/volume) deve constar na UI e no runbook?
10. Que reconciliação é exigida antes de reabrir workers após restore, especialmente para filas Redis perdidas e operações de mídia/crédito duráveis?
