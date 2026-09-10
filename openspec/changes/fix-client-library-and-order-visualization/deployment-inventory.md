# Inventário de deploy em homologação

## Estado implantado

- Change: `fix-client-library-and-order-visualization`.
- Branch integrada: `feature/fix-client-library-and-order-visualization`.
- Base da implementação: `0d48ab8de41f8ad59ee26439c9a3edd876e34727`, igual a `origin/develop` no início desta change.
- SHA de implementação validada: `2573f8c7ab8cf3359d444094dafb1b5278b7eda4`.
- SHA integrado e publicado em homologação: `67dbd2933616d2005363db97c1fca9c6b66804bc`.
- Destino previsto: `https://markina-homolog.duckdns.org`.
- Migration: nenhuma.
- Alterações de runtime: somente frontend; backend de produção, workers, filas, reconhecimento facial, preços, PIX, WhatsApp, mídia, banco e dados permanecem inalterados.
- Autorização humana de push, merge, deploy e acompanhamento: concedida em `2026-09-10`.
- Pull request integrado: `#63` (`https://github.com/conradodeita/markina-gallery/pull/63`).
- Workflow de `develop`: execução `34540912766`, concluída com backend, frontend, Gitleaks, OpenSpec e `deploy-homolog` aprovados.

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

## Execução autorizada

1. O SHA integrado em `develop` foi confirmado e publicado exatamente como `67dbd2933616d2005363db97c1fca9c6b66804bc`.
2. O inventário remoto confirmou o projeto `markina-gallery`, entrada `127.0.0.1:8080`, subdomínio `markina-homolog.duckdns.org` e serviços saudáveis, sem remover o container órfão preexistente reportado pelo Compose.
3. O frontend foi publicado preservando API, dados, mídia, workers e serviços de terceiros; nenhuma migration foi executada.
4. `/healthz`, `/api/health` e `/library` responderam HTTP `200` após o deploy.
5. `FACIAL_PROCESSING_ENABLED=true` permaneceu inalterado e os workers faciais permaneceram saudáveis.
6. O roteiro autenticado foi executado sem selecionar fotos, informar/confirmar pagamento, enviar mídia ou alterar estado comercial; os resultados estão registrados em `homologation-checklist.md`.

## Rollback

Se o frontend falhar, retornar os serviços web/Nginx da Markina ao último SHA saudável. Como não há migration nem mudança de dados, o rollback não requer restauração de banco, mídia ou filas. Qualquer operação além desse rollback de aplicação exige novo inventário e nova autorização humana explícita.
