# Inventário de deploy em homologação

## Estado candidato

- Change: `fix-client-library-and-order-visualization`.
- Branch local: `feature/fix-client-library-and-order-visualization`.
- Base da implementação: `0d48ab8de41f8ad59ee26439c9a3edd876e34727`, igual a `origin/develop` no início desta change.
- SHA de implementação validada: `2573f8c7ab8cf3359d444094dafb1b5278b7eda4`.
- SHA candidato de deploy: SHALL ser confirmado depois da integração em `develop`; o deploy MUST publicar exatamente o SHA integrado.
- Destino previsto: `https://markina-homolog.duckdns.org`.
- Migration: nenhuma.
- Alterações de runtime: somente frontend; backend de produção, workers, filas, reconhecimento facial, preços, PIX, WhatsApp, mídia, banco e dados permanecem inalterados.
- Autorização de push, merge e deploy desta change: pendente.

## Topologia preservada

- Projeto/arquivo: `--env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml`.
- Checkout remoto exclusivo: `/opt/markina-gallery`.
- Única entrada publicada pela Markina: `127.0.0.1:8080`, atrás do proxy existente; Nginx interno em `80`, web em `3000` e API em `8000` somente na rede do projeto.
- PostgreSQL e Redis não publicam portas.
- Serviços preservados: `nginx`, `web`, `api`, `migrate`, `worker`, `db`, `redis`, `face-index-worker`, `face-search-worker`, `face-maintenance-worker`; Evolution permanece no estado já existente.
- Volumes preservados: `pgdata`, `redisdata`, `media-source`, `media-derivatives`, `media-history`, `facial-references`, `evolution-instances`, `evolution-pgdata` e `evolution-redisdata`.

## Impacto zero

- Não há migration, backfill, escrita administrativa, reenfileiramento ou transformação de fotos.
- Não executar `docker compose down`, prune, remoção de volumes, restore, migração destrutiva ou comando fora do projeto Markina.
- Não alterar proxy, DNS, certificados, firewall, redes, containers, imagens ou volumes de terceiros.
- Não alterar secrets nem `FACIAL_PROCESSING_ENABLED`; a configuração vigente SHALL ser preservada.
- O teste backend adicionado apenas comprova que `/library` permanece em `15` consultas e `/library/purchases` em `6` consultas ao crescer de uma para cinco galerias/pedidos; nenhuma alteração backend de runtime foi necessária.

## Ordem proposta após autorização

1. Confirmar o SHA integrado em `develop` e os checks focados desta change.
2. Inventariar no host o SHA remoto, containers, portas, volumes, espaço e estado facial antes da publicação.
3. Publicar o frontend no SHA integrado usando exclusivamente o projeto Markina; preservar API, dados, mídia, workers e serviços de terceiros.
4. Confirmar containers saudáveis e HTTP `200` em `/healthz`, `/api/health` e `/library`.
5. Executar o roteiro autenticado em `homologation-checklist.md` no desktop e no celular.

## Rollback

Se o frontend falhar, retornar os serviços web/Nginx da Markina ao último SHA saudável. Como não há migration nem mudança de dados, o rollback não requer restauração de banco, mídia ou filas. Qualquer operação além desse rollback de aplicação exige novo inventário e nova autorização humana explícita.
