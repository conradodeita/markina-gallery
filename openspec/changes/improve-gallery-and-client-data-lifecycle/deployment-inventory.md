# Inventário de release e plano de impacto zero

## Estado vigente da preparação — 12/11/2026

**Alvo decidido pelo proprietário:** integrar o SaaS ao servidor de produção já operado; não há homologação separada para este release. A decisão de 11/11/2026 em `../add-small-multi-photographer-pilot/design.md` substitui o alvo de homologação descrito no inventário histórico abaixo. A autorização de 31/08/2026 registrada para homologação não autoriza publicação, migration, teste com escrita ou qualquer operação em produção.

### Inventário remoto somente leitura

Consulta SSH read-only de 12/11/2026, limitada ao projeto Compose `markina-gallery`; nenhum registro de cliente, conteúdo, segredo ou backup foi consultado.

- 13/13 containers do projeto estavam `Up` e `healthy`: API, web, Nginx do app, PostgreSQL, Redis, worker geral, workers faciais/de índice/manutenção, worker de ajuste de prévia e Evolution API com PostgreSQL/Redis auxiliares.
- Única porta publicada observada: Nginx do app em `127.0.0.1:8080 -> 80/tcp`. API (`8000`), web (`3000`), bancos e Redis não tinham porta publicada diretamente no host. Nginx Proxy Manager/proxy externo não foi inspecionado.
- `alembic current` dentro da API retornou `20261026_0090 (head)`.
- Checkout remoto `/opt/markina-gallery`: SHA `0dd015a62447e0c8d4c6af16b381140c8118f2ec`, sem alterações em `git status`; `git branch --show-current` não retornou branch (checkout destacado). Isso não prova por si só qual commit gerou cada container ativo.
- Branch local `feature/saas-release-candidate`, HEAD `855be42b826c61c8ebdb2bd1e471ca1d28147061`; a única head Alembic local é `20261111_0125`, 35 revisões depois do schema remoto. `git status --short --untracked-files=all` contabilizou 697 entradas; nenhuma SHA isolada de candidato foi preparada. Preservar todas as mudanças existentes.
- Foram conferidos somente os estados/portas dos containers e a revisão Alembic. Healthchecks HTTP externos, proxy, backups/restauração e conteúdo de configuração não foram consultados nesta atualização.

### Avaliação de prontidão

**NO-GO para executar agora a task 8.6 ou publicar.** A saúde atual dos containers não comprova compatibilidade do candidato, ausência de impacto ou restauração. A produção está em `0090`, o código local em `0125`, ainda não existe candidato isolado e o worktree tem 697 entradas pendentes. O estado de backup/restauração não foi verificado. O fluxo protegido de release de aplicação existente aceita somente API/web e proíbe migrations, Compose e workers; portanto, não cobre esta mudança. A migração e a validação abrangente ainda não têm um procedimento de release compatível comprovado.

O “impacto zero” é uma meta do plano, não uma garantia. A API e a web podem sofrer interrupção breve quando recriadas, e o impacto de locks/backfills do banco em dados produtivos não foi medido. Como o proprietário determinou que o sistema em produção continue atendendo clientes, qualquer etapa com risco de indisponibilidade deve parar antes da execução e ser apresentada para autorização específica.

### Plano de preparação e gates

1. Preservar o worktree e concluir o checklist pré-release definido pelo proprietário; não limpar nem selecionar automaticamente os 697 caminhos e não enviar push antes de atingir o gate de 100% já estabelecido.
2. Isolar um candidato revisável sem incluir mudanças não relacionadas. Revisar todas as revisions `0091–0125` e compatibilidade entre API, web, workers e schema; repetir a cadeia completa `0090→0125` em PostgreSQL descartável. A evidência sintética não substitui medição de lock/backfill representativa.
3. Comprovar backup recente, integridade e ensaio de restauração antes de qualquer mudança de schema. Definir separadamente rollback de aplicação e recuperação do banco; não presumir que `alembic downgrade` seja seguro após a criação de dados de negócio.
4. Criar ou aprovar um fluxo de release que cubra exatamente as imagens e migrations necessárias, sem incluir outros projetos/serviços; o procedimento API/web existente não pode ser ampliado por inferência.
5. Antes de qualquer publicação em produção, repetir inventário somente leitura no SHA exato: host/projeto, serviços e imagens, portas/domínio, revisão/schema, espaço/volumes, backup/restore e rollback. Apresentar o plano completo e aguardar autorização operacional específica.
6. Somente após release autorizado e confirmação de que nenhuma etapa exigirá interrupção não aprovada, manter o cadastro público fechado e executar a validação com a conta do proprietário e dados estritamente sintéticos, sem fotos, pedidos ou dados de clientes. Registrar SHA, migration, healthchecks, isolamento e aceite visual; se qualquer condição divergir, parar e manter o cadastro fechado.

**Gate atual:** preparação documental/read-only concluída; sem autorização para push, publicação, migration, criação/exclusão de dados sintéticos em produção ou reinício de serviços. Em 12/11/2026 o proprietário aprovou classificar a task 8.6 como aceite operacional pós-release, fora do percentual de prontidão pré-release de 100%. Essa classificação não concede autorização de publicação ou operação.

## Inventário histórico de homologação — 31/08/2026 (alvo substituído)

Estado preparado e autorizado pelo proprietário em 2026-08-31 para a change
`improve-gallery-and-client-data-lifecycle`. A autorização cobre integração,
aprovação do Environment e deploy deste inventário exclusivamente em homologação;
qualquer ampliação para produção ou alteração de recursos externos continua proibida.

## Alvo e gate de versão

- Ambiente: `homolog`, em `/opt/markina-gallery`.
- Projeto/arquivo obrigatórios: `--env-file docker/.env.homolog -p
  markina-gallery -f docker/docker-compose.yml`.
- Subdomínio existente: `https://markina-homolog.duckdns.org`.
- Entrada local esperada: somente `127.0.0.1:8080`, encaminhada ao Nginx
  interno pelo alias exclusivo `markina-homolog-nginx` na `npm-network`.
- O SHA alvo será criado, integrado em `develop` e aprovado pelos
  jobs `backend`, `frontend`, `openspec` e `gitleaks`. O deploy SHALL recusar
  worktree sujo, SHA fora de `origin/develop` ou origem Git divergente.

## Topologia e isolamento

Os serviços persistentes da aplicação permanecem `nginx`, `web`, `api`,
`worker`, `db` e `redis`; `migrate` é efêmero. Se o perfil WhatsApp real já
estiver ativo, `evolution-api`, `evolution-db` e `evolution-redis` permanecem
internos e SHALL conservar exatamente a configuração homologada existente.

O Compose renderizado publica somente o Nginx. `web:3000`, `api:8000`, bancos,
Redis e Evolution permanecem apenas nas redes Docker da Markina. Nenhum
container, porta, volume, rede, proxy, DNS, firewall ou certificado de outro
projeto pode ser alterado.

## Banco e migrations

O head alvo é `20260831_0031`. O lote aditivo/transformacional compreende
`0018` a `0031`: operações duráveis de ciclo de vida, snapshots comerciais,
estado de exclusão, procedência e unicidade da privada, identidade por telefone,
capacidades opacas, retenção, lease/cancelamento do worker, backfill de vínculos,
contexto de autenticação, retenção de mídia privada, herança da Galeria pública e
minimização de PII do OTP.

As migrations foram validadas em PostgreSQL 17 descartável por
`upgrade head`, downgrade de `0031` para `0030` e novo `upgrade head`. O deploy
real SHALL criar o dump lógico antes de executar Alembic e confirmar
`20260831_0031 (head)` depois. Transformações recusam dados legados ambíguos ou
downgrade com remoção já iniciada; uma recusa mantém o banco para diagnóstico e
bloqueia rollback automático.

## Configuração e segredos

- `AUTH_PII_FINGERPRINT_SALT` é novo, obrigatório fora de desenvolvimento e
  SHALL receber valor aleatório exclusivo de homologação tanto na API quanto no
  worker. Quando ausente ou vazio, o script autorizado gera 32 bytes aleatórios
  no próprio servidor, grava o valor somente em `docker/.env.homolog` com
  permissão restrita e nunca o imprime; valor existente curto ou duplicado
  interrompe o deploy para reconciliação.
- `AUTH_OTP_PII_RETENTION_MINUTES` mantém padrão `60` e
  `AUTH_OTP_CLEANUP_INTERVAL_SECONDS` mantém padrão `60`, salvo decisão
  operacional explícita.
- `COMMERCIAL_HISTORY_MEDIA_RETENTION_DAYS` SHALL permanecer vazio enquanto não
  houver decisão documentada do controlador dos dados. Vazio não expurga mídia
  histórica.
- As credenciais Evolution/WhatsApp existentes não mudam e não devem ser
  reemitidas, impressas ou copiadas por este deploy.

## Armazenamento

O Compose mantém `pgdata`, `redisdata`, `media-source` e `media-derivatives` e
adiciona o volume exclusivo `media-history`, montado somente em API e worker em
`/var/lib/markina/history`. Esse volume guarda apenas prévia protegida mínima e,
quando necessário, entrega histórica ou sua referência; ele não substitui nem
duplica indiscriminadamente os originais operacionais.

Antes do deploy, o operador SHALL registrar espaço livre, tamanho dos volumes
Markina e o manifesto das imagens. O novo volume deve ser criado pelo próprio
Compose e nunca compartilhado com outro projeto. Nenhum volume será removido,
renomeado ou podado.

## Plano de impacto zero

1. Confirmar SHA integrado em `develop`, CI verde e a autorização explícita deste
   inventário registrada em 2026-08-31.
2. Fazer inventário remoto somente leitura de containers, Compose, portas,
   redes, volumes, revisão Alembic, SHA saudável e espaço livre; interromper se
   aparecer recurso externo ao projeto `markina-gallery`.
3. Validar o checkout limpo, garantir permissão restrita de
   `docker/.env.homolog`, preservar ou gerar no servidor o novo salt sem
   imprimir o valor e
   `docker compose ... config --quiet`.
4. Registrar SHA/revisão/imagens anteriores e criar dump lógico exclusivo em
   `/var/lib/markina-gallery/backups`; preservar todos os volumes de mídia.
5. Executar somente o workflow protegido e `scripts/deploy-homolog.sh`. O script
   seleciona o SHA, constrói/executa `migrate`, preserva o perfil WhatsApp e
   recria apenas `api`, `web`, `worker` e o Nginx interno da Markina.
6. Confirmar serviços saudáveis, mount `media-history`, Alembic no head e SHA em
   `/var/lib/markina-gallery/deploy-state/last-healthy.sha`.
7. Testar internamente e externamente `/healthz` e `/api/health`; confirmar que o
   webhook interno continua não exposto. Só depois iniciar os testes sintéticos
   e a revisão visual humana previstos na task 8.6.

## Rollback e recuperação

- Antes de qualquer mudança de schema, o script pode voltar somente o código ao
  SHA anterior e recriar os serviços Markina.
- Depois que Alembic começar, não há rollback automático. Uma falha SHALL
  preservar banco, containers e volumes para diagnóstico; não se usa downgrade
  improvisado, `docker compose down`, prune ou restauração automática.
- Se a reversão após mudança de schema for aprovada, o caminho conservador é
  restaurar o SHA anterior e o dump lógico pré-deploy de forma coordenada. Os
  volumes de mídia permanecem preservados; restauração ou reconciliação de mídia
  exige autorização humana específica e verificação por manifesto/checksum.
- Todos os healthchecks e a revisão Alembic devem ser repetidos antes de registrar
  a versão anterior como saudável.

## Condições humanas restantes

A autorização explícita do inventário/deploy foi concedida em 2026-08-31.
Permanecem a integração do SHA em `develop`, CI verde, aprovação do Environment
`homolog` e aceite visual dos fluxos do fotógrafo e da cliente no ambiente
publicado. A revisão visual local não substitui esse aceite.
