# Entrega contínua em homologação — Markina Gallery

O workflow `CI` publica em homologação somente após um push integrado em `develop` concluir os jobs `backend`, `frontend`, `openspec` e `gitleaks`. O job `deploy-homolog` usa o GitHub Environment `homolog`; configure nele revisores obrigatórios antes de habilitar a primeira publicação.

## Limites operacionais

- Alvo exclusivo: `/opt/markina-gallery`, projeto Compose `markina-gallery` e arquivo `docker/docker-compose.yml`.
- O script recusa checkout sujo, SHA fora de `origin/develop`, origem Git diferente do repositório GitHub esperado e configuração Compose inválida.
- São recriados somente `api`, `web`, `worker` e o Nginx interno da Markina. Não há `docker compose down`, prune, remoção de volumes ou alteração de ClearBudget, proxy, DNS, firewall, certificados e redes de terceiros.
- Antes da migration, é criado um dump lógico exclusivo em `/var/lib/markina-gallery/backups`. O banco **nunca** é restaurado automaticamente.
- Em falha sem mudança de revisão Alembic, o script pode voltar apenas o código e os serviços Markina ao SHA anterior. Se a revisão do schema mudou, ele para para decisão humana.

## Bootstrap externo único

Execute estas ações somente após inventário aprovado de containers, portas, subdomínio e impacto zero no servidor compartilhado:

1. Crie o Environment GitHub `homolog`, ative aprovação obrigatória e configure, sem valores no Git, os secrets `HOMOLOG_SSH_HOST`, `HOMOLOG_SSH_PORT`, `HOMOLOG_SSH_USER`, `HOMOLOG_SSH_PRIVATE_KEY`, `HOMOLOG_SSH_KNOWN_HOSTS` e `HOMOLOG_PUBLIC_BASE_URL`.
2. Crie uma chave de leitura exclusiva da Markina no servidor e configure o `origin` de `/opt/markina-gallery` para o repositório GitHub. A chave não pode dar escrita ao repositório nem acesso a outros projetos.
3. Crie, com permissão restrita ao usuário da Markina, `/var/lib/markina-gallery/deploy-state` e `/var/lib/markina-gallery/backups`.
4. Verifique que o checkout está limpo, que `docker/.env.homolog` existe fora do Git e que `docker compose --env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml config --quiet` é aprovado.
5. Aprove o primeiro job pendente do Environment e confirme no servidor o SHA registrado em `/var/lib/markina-gallery/deploy-state/last-healthy.sha`, os healthchecks `https://<host>/healthz` e `https://<host>/api/health`, sem expor credenciais em logs.

## Recuperação

Para recuperar uma falha com schema inalterado, reexecute o workflow com o SHA saudável por procedimento aprovado. Se qualquer migration tiver sido aplicada, interrompa e avalie compatibilidade e restauração de banco com aprovação humana explícita. Nunca use `git reset --hard`, `git checkout -- .`, `git clean`, `docker compose down` sem escopo nem restore automático de banco.
