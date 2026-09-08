# Inventário de homologação — autenticação

Data da coleta: 2026-08-25. Todas as inspeções foram feitas por SSH em modo somente-leitura; nenhum recurso do servidor foi criado, alterado, reiniciado ou removido.

## Servidor

- Host: `132.145.193.169` (`clearbudget-vnic`), Oracle Linux ARM64.
- Docker: 28.1.1, driver `overlay2`.
- Disco raiz: 194 GB totais, 27 GB usados, 167 GB livres (14%).

## Recursos existentes que não podem sofrer impacto

| Recurso | Estado/porta | Proteção exigida |
|---|---|---|
| Compose `clearbudget` | 4 containers em execução | Não alterar containers, rede, volumes nem o compose em `/home/ubuntu/docker/clearbudget/` |
| Frontend `firefly_frontend` | porta pública 3000 | A porta 3000 está indisponível para a Markina Gallery |
| Nginx Proxy Manager | portas públicas 80, 81 e 443 | É o único candidato a expor um subdomínio; nenhuma configuração será alterada sem aprovação |
| Portainer | portas públicas 8000 e 9443 | Portas indisponíveis |
| Docker networks | `clearbudget_default`, `npm-network` e redes padrão | Não reutilizar ou alterar sem avaliação explícita |
| Docker volumes | volume do projeto existente e `portainer_data` | Não alterar nem remover |

PostgreSQL do ClearBudget não publica porta no host e deve permanecer independente da Markina Gallery.

## Proposta de impacto zero para aprovação

- Diretório: `/opt/markina-gallery`, com permissões concedidas apenas para o usuário/serviço da Markina Gallery.
- Compose: sempre `docker compose -p markina-gallery -f docker/docker-compose.yml`.
- Serviços internos: PostgreSQL e Redis sem portas publicadas.
- Entrada local: Nginx da Markina Gallery ligado somente a `127.0.0.1:8080`; a porta 8080 estava livre durante o inventário.
- Entrada externa: um novo subdomínio de homologação configurado no Nginx Proxy Manager existente para encaminhar apenas à porta local 8080. O subdomínio ainda não foi definido.
- Banco, Redis, volumes, segredos e adaptador WhatsApp sandbox exclusivos do ambiente de homologação.
- É proibido usar `docker system/container/volume/network prune` ou `docker compose down` fora do projeto `markina-gallery`.

## Gate pendente

O proprietário precisa aprovar explicitamente esta proposta, incluindo o uso da porta local `127.0.0.1:8080` e informar o subdomínio de homologação desejado. Até essa aprovação, nenhuma alteração externa será executada.

## Aprovação recebida

- Porta local aprovada: `127.0.0.1:8080`.
- Subdomínio aprovado: `markina-homolog.duckdns.org`.
- DNS confirmado em 2026-08-25: `markina-homolog.duckdns.org` resolve para `132.145.193.169`.
