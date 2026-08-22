# Checklist de deploy e rollback — PhotoCRM

Limitado ao PhotoCRM. Nunca afeta containers, imagens, redes, volumes, proxy, firewall, DNS ou certificados de outros projetos.

## 0. Gate obrigatório (antes de qualquer ação em homologação/produção)

- [ ] Inspeções seguras concluídas: `docker ps`, `docker compose ls`, redes, volumes, serviços systemd, portas ocupadas
- [ ] Inventário encontrado apresentado ao proprietário
- [ ] Portas e subdomínio escolhidos apresentados ao proprietário
- [ ] Plano de impacto zero apresentado e **aprovação explícita** recebida

## 1. Preparação (uma vez por servidor)

- [ ] Diretório próprio do PhotoCRM criado (ex.: `/opt/photocrm`)
- [ ] Usuário/serviço próprio do PhotoCRM, quando aplicável
- [ ] `docker/.env.<ambiente>` criado fora do Git, com permissões restritas e segredos fortes gerados (`secrets.token_urlsafe`)
- [ ] Subdomínio próprio apontado no proxy reverso existente, sem alterar rotas de outros projetos
- [ ] Diretórios próprios de backups e logs criados

## 2. Deploy (por ambiente, homolog antes de prod)

- [ ] Código na branch correta (release/`main` após PR aprovado)
- [ ] `docker compose -p photocrm -f docker/docker-compose.yml config` válido
- [ ] Imagens construídas: `docker compose -p photocrm -f docker/docker-compose.yml build`
- [ ] Stack sobe: `docker compose -p photocrm -f docker/docker-compose.yml up -d`
- [ ] Healthchecks verdes: `docker compose -p photocrm -f docker/docker-compose.yml ps`
- [ ] Smoke test: `curl https://<subdominio>/healthz` e `curl https://<subdominio>/api/health`
- [ ] Nenhum segredo em logs (revisar saída dos containers)
- [ ] Validação OpenSpec da mudança: `openspec validate --strict`
- [ ] Varredura de segredos: gitleaks sem achados
- [ ] Backups do banco confirmados (manuais até a mudança `media-storage`)

## 3. Rollback (somente o PhotoCRM)

- [ ] Identificar versão anterior saudável (imagem/tag ou commit)
- [ ] `docker compose -p photocrm -f docker/docker-compose.yml up -d` com a versão anterior
- [ ] Healthchecks verdes e smoke test repetidos
- [ ] Se necessário, restaurar banco a partir do backup do dia (procedimento de restauração testado em homologação)
- [ ] Registrar incidente e causa no relatório do proprietário

## 4. Pós-deploy

- [ ] Sincronizar/arquivar a mudança OpenSpec correspondente (somente specs implementadas)
- [ ] Atualizar `docs/DECISOES-TECNICAS.md` se houver decisão nova
- [ ] Confirmar que nenhum artefato do outro projeto foi alterado
