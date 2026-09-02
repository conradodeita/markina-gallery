# Inventário pré-deploy de homologação

Inventário preparado em 2026-09-02 para a change
`consolidate-shared-private-galleries-and-progressive-sales`. Nenhuma ação
remota, migration ou publicação foi executada durante sua preparação.

## Artefato e gate de integração

- Base anterior ao artefato: `2737de197fd3e2b914ec319f6015b4351ce6040e`.
- Branch de origem: `codex/consolidate-shared-private-galleries`.
- SHA funcional testado: `c0e1aedeeaa1bc867c8a29d47b461bfb5b1bc2c0`.
- SHA do hardening de deploy: `9d7a54c6f98a0ac6972441e95513e41ae4d52398`.
- O SHA efetivamente implantado SHALL ser o commit de integração em `develop`
  que contenha `9d7a54c6f98a0ac6972441e95513e41ae4d52398` como ancestral.
- Resultados locais: backend `235 passed, 1 skipped`; matriz sintética com
  `8 passed`; frontend `117 passed`; Ruff, TypeScript, lint sem erros, build,
  Compose e OpenSpec estrito aprovados.
- Push, integração, aprovação do Environment e deploy dependem de autorização
  humana específica para este inventário.

## Alvo, portas e isolamento

- Ambiente: `homolog`, checkout exclusivo `/opt/markina-gallery`.
- Compose obrigatório: `--env-file docker/.env.homolog -p markina-gallery -f
  docker/docker-compose.yml`.
- Subdomínio existente: `https://markina-homolog.duckdns.org`.
- Única entrada publicada: `127.0.0.1:8080`, encaminhada ao Nginx interno pelo
  alias exclusivo `markina-homolog-nginx` na rede preexistente `npm-network`.
- `web:3000`, `api:8000`, PostgreSQL, Redis e Evolution continuam internos às
  redes Docker. Não há porta, DNS, certificado, firewall ou proxy novo.

## Schema, migrations e dados

- Head esperado: `20260901_0040`.
- Cadeia aditiva nova: `20260901_0034` a `20260901_0040`, linear sobre
  `20260831_0033`.
- As revisions adicionam associação multiusuário e backfill, capacidades
  reconstruíveis, notificações de membros, presets progressivos/snapshots,
  fonte PIX copia-e-cola, unicidade de referências compartilhadas e origens
  por foto privada.
- O pré-diagnóstico aborta conflito de mais de uma privada para o mesmo par
  origem/cliente. Não há mescla silenciosa, exclusão de cliente, pedido,
  pagamento, histórico ou mídia original.
- Antes de Alembic, o script SHALL criar dump lógico exclusivo da Markina em
  `/var/lib/markina-gallery/backups`. Não está autorizado downgrade, limpeza
  automática ou restauração sem novo inventário.

## Serviços, dependências e volumes

- Serviços persistentes continuam `nginx`, `web`, `api`, `worker`, `db` e
  `redis`; `migrate` permanece efêmero. O perfil `whatsapp-real` preserva
  `evolution-api`, `evolution-db` e `evolution-redis`.
- A dependência backend `qrcode` gera o QR PIX no servidor. Não há serviço ou
  volume novo.
- Volumes permanecem `pgdata`, `redisdata`, `media-source`,
  `media-derivatives`, `media-history`, `evolution-instances`,
  `evolution-pgdata` e `evolution-redisdata`.
- É proibido `docker compose down`, prune, remoção/rename de volume, conexão a
  rede de terceiro ou alteração dos containers de outros projetos.

## Configuração segura requerida

- Nova variável obrigatória: `GALLERY_CAPABILITY_SIGNING_KEY`, segredo aleatório
  exclusivo com no mínimo 32 bytes, diferente de
  `AUTH_PII_FINGERPRINT_SALT`.
- O script autorizado gera esse valor no próprio servidor quando ausente,
  grava-o atomicamente com permissão `0600`, valida comprimento e separação e
  nunca imprime o segredo.
- O valor SHALL ser configurado somente no mecanismo seguro já usado pelo
  servidor/Environment e exposto ao Compose por `docker/.env.homolog`, sem ser
  impresso, lido em relatório ou persistido no Git.
- As demais credenciais e configurações permanecem inalteradas.

## Plano de impacto zero

1. Após autorização específica, publicar e integrar somente esta change em
   `develop`; aguardar `backend`, `frontend`, `openspec` e `gitleaks` verdes.
2. Aprovar o Environment `homolog` somente para o SHA de integração que contém
   o SHA funcional testado.
3. Usar exclusivamente `.github/workflows/ci.yml` e
   `scripts/deploy-homolog.sh`, que validam origem, worktree, SHA, Compose e
   revisão Alembic antes de qualquer alteração.
4. Inventariar somente recursos rotulados do projeto `markina-gallery`, criar
   o dump lógico e executar `alembic upgrade head`.
5. Recriar apenas `api`, `web`, `worker` e `nginx`; preservar banco, Redis,
   Evolution, redes e volumes.
6. Confirmar o SHA publicado, `20260901_0040 (head)`, saúde dos containers e
   respostas `200` em `/healthz` e `/api/health`, internas e externas.
7. Executar smoke com telefone, JPEG, cliente, pedido e comunicação totalmente
   sintéticos; não usar biometria, criança ou dado pessoal real.

## Rollback e recuperação

- Antes da migration, falha permite restaurar somente o SHA saudável anterior
  e recriar os serviços Markina.
- Depois do início da migration, não haverá downgrade/restauração automática.
  Banco, dump, containers e volumes ficam preservados para diagnóstico.
- Qualquer restauração, downgrade abaixo de `0040`, remoção de associação ou
  reconciliação de mídia exige novo inventário e nova autorização humana.

## Gates humanos restantes

Restam autorização específica deste inventário, push/integração, migration e
deploy protegido em homologação; depois, revisão humana autenticada desktop e
mobile. A change não será sincronizada nem arquivada antes desse aceite.
