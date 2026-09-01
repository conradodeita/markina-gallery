# Inventário pré-deploy de homologação

Inventário preparado em 2026-09-01 para a change
`remediate-gallery-workflow-and-payment-experience`. Nenhuma ação remota foi
executada durante sua preparação. Publicação, aprovação do Environment e
migration em homologação dependem de autorização humana específica para este
inventário.

## Artefato e gate de integração

- SHA funcional testado: `fc28b6704046bd07ac0dc55519818cd033368ee1`.
- Branch de origem: `feature/remediate-gallery-workflow-and-payment-experience`.
- Base verificada: `922dd0c074202ab5471062969fe5c63cf7b0cb21`, então
  `origin/develop`.
- O SHA efetivamente publicado SHALL ser o commit que integrar este artefato em
  `develop`; ele deverá conter `fc28b67` como ancestral e passar pelos jobs
  `backend`, `frontend`, `openspec` e `gitleaks` antes do job protegido
  `deploy-homolog`.
- Resultados locais do artefato: backend 200 aprovados/1 ignorado; frontend 103
  aprovados; Ruff, TypeScript, build e lint sem erros; OpenSpec 25/25.

## Alvo, porta e subdomínio

- Ambiente exclusivo: `homolog`, checkout `/opt/markina-gallery`.
- Compose obrigatório: `--env-file docker/.env.homolog -p markina-gallery -f
  docker/docker-compose.yml`.
- Subdomínio existente: `https://markina-homolog.duckdns.org`.
- Única entrada publicada esperada: `127.0.0.1:8080`, encaminhada ao Nginx
  interno pelo alias exclusivo `markina-homolog-nginx` na rede externa
  preexistente `npm-network`.
- `web:3000`, `api:8000`, PostgreSQL, Redis e Evolution permanecem somente nas
  redes Docker. Não há nova porta, DNS, certificado, firewall ou rota de proxy.

## Schema e dados

- Head esperado: `20260831_0033`.
- Migration nova: `20260831_0033_photo_folder_purpose.py`, aditiva sobre
  `20260831_0032`.
- A coluna `photo_folder.purpose` recebe `content | cover_assets`, com backfill
  conservador `content`; um índice único parcial limita a uma pasta técnica de
  capa por Galeria pública.
- A migration não exclui pasta, foto, privada, vínculo, pedido, comunicação ou
  snapshot. Upgrade do zero e ciclo `0032 → 0033 → 0032 → 0033` foram
  validados em banco temporário.
- O deploy SHALL criar dump lógico exclusivo da Markina antes de executar
  Alembic e confirmar `20260831_0033 (head)` após a subida. Nenhum downgrade ou
  limpeza automática está autorizado.

## Assets, serviços e volumes

- O frontend adiciona dependências fixadas Fontsource `5.3.0` para Montserrat,
  Playfair Display, Caveat e Dancing Script. O build importa somente quatro
  WOFF2 variáveis latinos normais, total aproximado de 189,5 KiB, servidos pelo
  próprio domínio.
- A licença SIL OFL 1.1 integral está em `frontend/licenses/OFL-1.1.txt` e os
  avisos em `frontend/FONT_LICENSES.md`. Não há `@import`, Google Fonts nem
  requisição de fonte a terceiro em runtime.
- Serviços persistentes permanecem `nginx`, `web`, `api`, `worker`, `db` e
  `redis`; `migrate` continua efêmero. O perfil `whatsapp-real`, se já ativo,
  conserva `evolution-api`, `evolution-db` e `evolution-redis` sem alteração.
- Volumes permanecem `pgdata`, `redisdata`, `media-source`,
  `media-derivatives`, `media-history`, `evolution-instances`,
  `evolution-pgdata` e `evolution-redisdata`. Nenhum volume novo, remoção,
  rename, prune ou compartilhamento com outro projeto.
- Não há variável de ambiente, segredo ou credencial nova nesta change.

## Plano de impacto zero

1. Depois da autorização específica, publicar a branch e integrar somente esta
   change em `develop`; aguardar os quatro jobs obrigatórios verdes e a
   aprovação do Environment `homolog`.
2. O workflow deverá fazer inventário remoto somente leitura e recusar origem
   Git divergente, worktree sujo, SHA fora de `origin/develop`, recurso externo
   ao projeto ou Alembic inesperado.
3. Registrar SHA saudável, revisão Alembic, imagens, containers e espaço dos
   volumes Markina; validar o Compose com o arquivo seguro sem imprimir valores.
4. Criar dump lógico em `/var/lib/markina-gallery/backups` e preservar todos os
   volumes de mídia antes de `alembic upgrade head`.
5. Executar exclusivamente `.github/workflows/ci.yml` e
   `scripts/deploy-homolog.sh`. O script recria apenas serviços da Markina e não
   executa `docker compose down`, prune, alteração de proxy ou restauração.
6. Confirmar SHA publicado, `20260831_0033 (head)`, containers saudáveis e os
   healthchecks interno/externo `/healthz` e `/api/health`.
7. Executar smoke somente com identidade, telefone, JPEG, pedido e comunicação
   sintéticos; não enviar dado real nem alterar a configuração Evolution.

## Rollback e recuperação

- Antes da migration, uma falha pode restaurar apenas o SHA saudável anterior e
  recriar os serviços Markina.
- Depois do início da migration não há downgrade ou restauração automática. A
  falha preserva banco, dump, containers e volumes para diagnóstico.
- A aplicação anterior não deve aceitar upload adicional em pasta já publicada;
  essa ação fica desabilitada durante rollback para evitar semântica divergente.
- Qualquer restauração de dump, downgrade para `0032`, remoção de pasta técnica
  ou reconciliação de mídia exige novo inventário e autorização humana.
- Após rollback autorizado, repetir Alembic e ambos os healthchecks antes de
  registrar novamente o SHA anterior como saudável.

## Gates humanos restantes

Restam a autorização específica deste inventário, a publicação protegida em
homologação e a revisão humana autenticada das etapas 02–05, resumo, Pagamentos
e visualizações do fotógrafo/cliente em desktop e smartphone. A change não será
sincronizada nem arquivada antes desse aceite.
