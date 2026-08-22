# DEPLOY — PhotoCRM (homologação e produção)

> **Regra de ouro:** os servidores executam outros projetos. Toda ação é limitada ao PhotoCRM e nunca
> altera containers, imagens, redes, volumes, proxy, firewall, DNS ou certificados de terceiros.

## Ambientes

| Ambiente | Banco | Segredos | Integrações | Domínio |
|---|---|---|---|---|
| local | PostgreSQL do Compose local | `docker/.env` (não versionado) | sandbox | localhost |
| homolog | PostgreSQL exclusivo do PhotoCRM | `docker/.env.homolog` no servidor | homologação | subdomínio próprio |
| prod | PostgreSQL exclusivo do PhotoCRM | `docker/.env.prod` no servidor | produção | subdomínio próprio |

Cada ambiente tem banco, Redis, segredos, WhatsApp e integrações totalmente distintos.

## Isolamento obrigatório no servidor (Oracle)

- Diretório próprio do PhotoCRM (ex.: `/opt/photocrm`)
- Usuário/serviço próprio quando aplicável
- Projeto Compose exclusivo: `photocrm` — sempre `docker compose -p photocrm -f docker/docker-compose.yml ...`
- Redes, volumes e containers com prefixo `photocrm`
- Banco (PostgreSQL) e Redis exclusivos do PhotoCRM
- Portas internas próprias; no host, apenas o Nginx (porta definida no `.env` do ambiente)
- Subdomínio próprio no proxy reverso existente, **sem alterar rotas de outros projetos**
- Backups e logs em diretórios próprios do PhotoCRM
- Procedimento de deploy e rollback documentado e **limitado ao PhotoCRM**

## Antes de qualquer ação em homologação/produção (gate obrigatório)

1. Executar apenas inspeções seguras: `docker ps`, `docker compose ls`, redes, volumes, serviços systemd e portas ocupadas.
2. Apresentar ao proprietário: inventário encontrado, portas/subdomínio escolhidos e plano de impacto zero.
3. Aguardar aprovação explícita antes de qualquer mudança.

## Proibido em servidores compartilhados

- `docker system prune`, `docker container prune`, `docker volume prune`, `docker network prune`
- `docker compose down` sem o par `-p photocrm -f docker/docker-compose.yml`
- Alterar proxy reverso, firewall, DNS ou certificados existentes sem identificar com precisão o impacto

## Segredos

- Servidor: `docker/.env.homolog` e `docker/.env.prod` (fora do Git, permissões restritas ao usuário do serviço).
- CI: exclusivamente GitHub Secrets (`GITHUB_TOKEN` e secrets de workflow).
- Nunca em código, frontend, logs ou tabelas comuns; varredura com gitleaks na CI.

## Deploy e rollback

- Passo a passo por ambiente: `docs/CHECKLIST-DEPLOY-ROLLBACK.md`.
- Backups diários cifrados no Google Drive com restauração testada em homologação: implementados pela mudança do domínio `media-storage`; até lá, backups manuais constam do checklist.
- SMTP transacional com SPF/DKIM/DMARC será configurado na mudança do domínio `messaging`/`auth`.
