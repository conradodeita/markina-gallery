# Inventário pré-deploy de homologação

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
