# Inventário de deploy em homologação — 2026-09-09

## Entrega

- Change: `complete-private-gallery-operations-and-sales`.
- SHA de implementação validado: `86601639c506f3aabb145e875147f7e9c4b2191b`.
- O SHA implantado SHALL ser o merge commit em `develop` que contenha esse SHA e este inventário; o workflow e o script remoto conferem o SHA exato antes de trocar a aplicação.
- Migration aditiva esperada: `20260909_0052_private_gallery_operations_sales` sobre o head anterior `20260909_0051`.
- Estado facial obrigatório: `FACIAL_PROCESSING_ENABLED=true` e `FACIAL_MAX_REFERENCE_BYTES=31457280` (30 MB).

## Escopo e rede

- Host remoto: checkout exclusivo `/opt/markina-gallery`.
- Projeto Compose: `markina-gallery`, arquivo `docker/docker-compose.yml`, ambiente `docker/.env.homolog`.
- Subdomínio: `https://markina-homolog.duckdns.org`.
- Único bind da aplicação no host: `127.0.0.1:8080` para o Nginx Markina; web `3000`, API `8000`, PostgreSQL e Redis permanecem somente nas redes Docker.
- Rede interna dedicada: `markina-gallery_internal`; rede externa compartilhada `npm-network` somente é consumida pelo Nginx existente e SHALL NOT ser alterada.

## Serviços e volumes

- Aplicação: `nginx`, `web`, `api`, `worker`.
- Facial habilitado: `face-search-worker`, `face-index-worker`, `face-maintenance-worker`.
- WhatsApp real: `evolution-api`, `evolution-db` e `evolution-redis` somente quando já estiverem ativos para a Markina; o deploy não ativa infraestrutura externa nova.
- Volumes preservados: `pgdata`, `redisdata`, `media-source`, `media-derivatives`, `media-history`, `facial-references`, `evolution-instances`, `evolution-pgdata` e `evolution-redisdata`.

## Plano de impacto zero

1. Confirmar checkout, origin, árvore limpa, SHA esperado, containers/volumes/redes rotulados como Markina, uso de disco e ocupação da porta `8080`.
2. Criar `pg_dump -Fc` exclusivo do banco Markina em `/var/lib/markina-gallery/backups`, com manifesto de SHA anterior e alvo.
3. Fazer checkout detached do SHA exato, construir o serviço de migration e executar `alembic upgrade head`.
4. Atualizar somente `api`, `web`, `worker`, três workers faciais e recriar somente o Nginx da Markina. Preservar Evolution quando já ativo.
5. Não executar `docker compose down`, prune, remoção de volume, mudança de proxy, firewall, DNS, certificado ou recurso de terceiros.
6. Exigir healthchecks dos containers e de `http://127.0.0.1:8080/{healthz,api/health}` e do subdomínio público antes de registrar o SHA saudável.

## Backup e rollback

- Backup lógico obrigatório antes da migration, sem incluir bancos ou volumes de terceiros.
- Se a migration não alterar o schema, o script pode restaurar somente a versão anterior da aplicação.
- Como `0052` adiciona schema, downgrade e restauração do banco SHALL NOT ocorrer automaticamente. A estrutura aditiva permanece; a aplicação anterior só pode ser restaurada por procedimento revisado que confirme compatibilidade e preserve mídia privada, correções financeiras e reaberturas novas.
- O script registra `previous_sha`, `target_sha`, revisão Alembic anterior/nova e `last-healthy.sha`.

## Evidências pré-deploy

- Ruff aprovado.
- Backend completo percorrido em partições: 465 testes; após o endurecimento final, 145 testes das áreas afetadas foram percorridos e os três ajustes de expectativa legada reaprovados, além de cinco contratos críticos aprovados.
- Frontend: 30 arquivos/192 testes, lint sem erros, TypeScript e build aprovados.
- PostgreSQL 16 descartável: ciclo `head -> 0051 -> head` aprovado.
- OpenSpec estrito, Gitleaks e `git diff --check` aprovados.
- O ensaio `scripts/test_deploy_homolog.sh` não é executável nesta estação Windows sem `/bin/bash`; o mesmo teste permanece obrigatório no job Linux do CI antes do deploy.

## Autorização

O proprietário autorizou explicitamente merge e deploy desta entrega durante a execução da change. O inventário foi apresentado antes de qualquer ação remota de homologação. Revisão humana, sincronização das specs principais e arquivamento permanecem posteriores à validação em homologação.

## Atualização incremental do funil financeiro — 2026-09-12

- Commit funcional validado: `a2904c2af7ef52cc2f067c3ba125cbebb906042d`; o alvo remoto será o merge commit em `develop` que o contiver.
- Escopo: projeção e interface de `Valor das fotos selecionadas`, `Valor dos pedidos` comunicados e `Receita confirmada`, sem dupla contagem.
- Schema: nenhuma migration nova; o head esperado permanece `20260909_0052_private_gallery_operations_sales`.
- Dados e mídia: nenhuma limpeza, backfill, alteração de foto ou operação destrutiva.
- Serviços afetados pelo código: `api` e `web`; o workflow preserva volumes e recria somente os serviços Markina previstos pelo script aprovado.
- Estado facial: `FACIAL_PROCESSING_ENABLED=true` e workers faciais saudáveis continuam obrigatórios, sem nova operação de rollout.
- Entrada e isolamento: `https://markina-homolog.duckdns.org`, bind `127.0.0.1:8080`, projeto Compose `markina-gallery`; nenhum recurso de terceiros será alterado.
- Rollback: como não há mudança de schema, restaurar somente a aplicação ao SHA saudável anterior `962ec11` caso os healthchecks ou a projeção financeira falhem; banco e volumes permanecem intactos.
- Autorização: o proprietário autorizou push, merge e deploy em homologação em 2026-09-12, após receber o inventário e o plano de impacto zero.
