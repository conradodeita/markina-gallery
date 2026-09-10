# Inventário de deploy em homologação

## Estado candidato

- Change: `persist-client-cart-and-simplify-client-portal`.
- Branch local: `feature/persist-client-cart-and-simplify-client-portal`.
- Base registrada antes da implementação: `7ca6c9407aef6d41451b916f792b7f50015fd028`.
- SHA de implementação validada: `2b25685bb6cb6ed62b07cc2396aa2e4e142ff941`.
- SHA candidato de deploy: SHALL ser confirmado depois da integração em `develop`; o deploy deverá publicar exatamente o SHA integrado, sem reconstruir a partir de outra referência.
- Destino: `https://markina-homolog.duckdns.org`.
- Migration aditiva: `20260910_0053_persistent_client_cart`.
- Alterações de runtime: API e frontend; nenhum worker, fila, mídia, preço, PIX, WhatsApp ou reconhecimento facial é alterado.
- Autorização de deploy desta change: pendente.

## Topologia preservada

- Projeto/arquivo: `--env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml`.
- Checkout remoto exclusivo: `/opt/markina-gallery`.
- Única entrada publicada pela Markina: `127.0.0.1:8080`, atrás do proxy existente; Nginx interno em `80`, web em `3000` e API em `8000` somente na rede do projeto.
- PostgreSQL e Redis não publicam portas.
- Serviços preservados: `nginx`, `web`, `api`, `migrate`, `worker`, `db`, `redis`, `face-index-worker`, `face-search-worker`, `face-maintenance-worker`; Evolution permanece no estado já existente.
- Volumes preservados: `pgdata`, `redisdata`, `media-source`, `media-derivatives`, `media-history`, `facial-references`, `evolution-instances`, `evolution-pgdata` e `evolution-redisdata`.

## Banco e impacto zero

A migration adiciona `sale_order.frozen_at`, índice comum e índice único parcial de rascunho. O backfill copia `created_at` para `frozen_at` em pedidos existentes; não apaga nem recalcula pedidos, itens, seleções, comunicações, clientes, galerias ou mídia.

- Fazer dump lógico exclusivo da Markina antes do Alembic.
- Não executar `docker compose down`, prune, remoção de volumes, restore automático ou comandos fora do projeto Markina.
- Não alterar proxy, DNS, certificados, firewall, redes, containers, imagens ou volumes de terceiros.
- Não reenfileirar mídia/facial e não alterar `FACIAL_PROCESSING_ENABLED`; o workflow vigente deve preservar `true` em homologação e comprovar workers saudáveis.
- Não executar downgrade automático depois que Alembic iniciar.

## Ordem proposta após autorização

1. Confirmar CI backend/frontend/OpenSpec/gitleaks verde e SHA integrado em `develop`.
2. Inventariar SHA remoto, head Alembic, containers, portas, volumes, espaço e estado facial imediatamente antes da publicação.
3. Criar backup lógico exclusivo da Markina.
4. Aplicar `20260910_0053`, publicar API/web no SHA exato e preservar os demais serviços.
5. Confirmar containers saudáveis e HTTP `200` em `/healthz`, `/api/health` e entrada do cliente.
6. Executar o roteiro humano em `homologation-checklist.md` sem editar pedidos existentes.

## Rollback

Se a aplicação falhar após a migration, retornar somente API/web/Nginx da Markina ao SHA saudável anterior e manter a coluna/índices aditivos. Não reconstruir seleções nem descongelar pedidos. Restore de banco ou downgrade exige novo inventário, análise dos pedidos criados depois da publicação e nova autorização humana explícita.
