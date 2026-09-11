# Inventário de deploy em homologação

## Estado candidato

- Change: `persist-client-cart-and-simplify-client-portal`.
- Branch local: `feature/persist-client-cart-and-simplify-client-portal`.
- Base registrada antes da implementação: `7ca6c9407aef6d41451b916f792b7f50015fd028`.
- SHA de implementação validada: `7d8bf4efb4b334e3a2d102bc7fb025dfe5ffc67f`.
- SHA integrado e publicado: `0d48ab8de41f8ad59ee26439c9a3edd876e34727`.
- Destino: `https://markina-homolog.duckdns.org`.
- Migration aditiva: `20260910_0053_persistent_client_cart`.
- Alterações de runtime: API e frontend; nenhum worker, fila, mídia, preço, PIX, WhatsApp ou reconhecimento facial é alterado.
- Autorização de deploy desta change: recebida nesta tarefa em 2026-09-10 antes do push, integração e aprovação do Environment `homolog`.

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

## Resultado — 2026-09-10

- PR `#62` integrado em `develop` por merge commit.
- Workflow `CI` `34511397653` aprovado no Environment `homolog` e concluído com sucesso.
- O inventário remoto restrito à Markina foi executado antes da mudança.
- Backup lógico exclusivo da Markina foi criado antes do Alembic.
- Migration confirmada: `20260909_0052 (head) -> 20260910_0053 (head)`.
- `FACIAL_PROCESSING_ENABLED=true` permaneceu persistido; workers faciais foram confirmados saudáveis antes e depois do deploy.
- SHA publicado e registrado como saudável: `0d48ab8de41f8ad59ee26439c9a3edd876e34727`.
- Healthchecks externos confirmados com HTTP `200` em `/healthz`, `/api/health` e na entrada do cliente.
- Nenhum dado, mídia, volume, rede, proxy, DNS, firewall, certificado ou recurso de terceiro foi removido ou alterado.

## Correção candidata — 2026-09-11

- Branch local: `feature/restore-client-gallery-entry`.
- Base `develop`: `217c2bb6e0401a6b17ec6f0d9c88ea071cf6ccf6`.
- SHA local validado: `3da6de98833b7435e087cfdd0d1016e92b29192e`.
- SHA de runtime saudável atualmente publicado: `67dbd2933616d2005363db97c1fca9c6b66804bc`; o workflow posterior `34543946062` está aguardando aprovação, mas contém somente documentação do deploy anterior e não altera o runtime.
- Destino proposto: `https://markina-homolog.duckdns.org`.
- Alteração: API inclui de forma aditiva a privada operacional já autorizada; frontend mostra `Minha galeria` sem depender do carrinho e carrega fotos/pastas progressivamente.
- Banco/migration: nenhuma alteração; não há escrita ou transformação de dados existentes.
- Serviços com nova imagem: `api` e `web`, publicados pelo workflow padrão da Markina; workers, filas, mídia, PostgreSQL, Redis, Evolution e recursos de terceiros permanecem preservados.
- Portas/subdomínio: sem mudança; entrada `127.0.0.1:8080` atrás do proxy existente em `markina-homolog.duckdns.org`, com `web:3000` e `api:8000` somente na rede interna do projeto.
- Estado facial: o workflow preserva `FACIAL_PROCESSING_ENABLED=true` e `FACIAL_MAX_REFERENCE_BYTES=31457280`; esta correção não altera processamento facial.
- Rollback: retornar somente aplicação Markina ao SHA saudável anterior, sem downgrade, restore, limpeza, remoção de volume ou mutação de dados.
- Validação local: frontend direcionado `27 passed`, backend direcionado `1 passed`, TypeScript, Ruff e OpenSpec aprovados; ESLint sem erros, com três avisos preexistentes de `<img>`; `git diff --check` sem erro.
- Autorização específica para push, merge e deploy desta correção: pendente.
