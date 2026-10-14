# Inventário pré-deploy — WhatsApp real em homologação

Estado preparado em 2026-08-30. Este documento não autoriza deploy nem pareamento.

## Alteração proposta

Adicionar à stack exclusiva `markina-gallery` três serviços internos sob o perfil `whatsapp-real`:

| Serviço | Imagem fixada | Limite | Porta publicada | Persistência |
| --- | --- | ---: | --- | --- |
| `evolution-api` | Evolution API 2.3.7 por digest | 0,75 CPU / 768 MiB | nenhuma | `evolution-instances` |
| `evolution-db` | PostgreSQL 15 Alpine por digest | 0,50 CPU / 256 MiB | nenhuma | `evolution-pgdata` |
| `evolution-redis` | Redis 7 Alpine por digest | 0,25 CPU / 128 MiB | nenhuma | `evolution-redisdata` |

Teto configurado: 1,5 CPU e 1.152 MiB para os três serviços. O consumo real deve ser medido após o bootstrap. A única publicação da Markina continua sendo o Nginx em `127.0.0.1:8080` no host de homologação; API, worker, Evolution, ambos os bancos e ambos os Redis permanecem internos.

## Impacto zero

- projeto/arquivo obrigatórios: `--env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml`;
- nenhum serviço Evolution entra na rede externa `npm-network`;
- nenhuma mudança em ClearBudget, outros projetos, proxy, DNS, firewall ou certificados;
- migration Markina é aditiva; banco e outbox de pagamento preexistentes são preservados;
- backup lógico Markina ocorre antes da troca de SHA;
- Evolution inicia antes de API/worker e ainda sem aparelho pareado;
- a API pública recusa `/api/internal/`; webhook circula diretamente na rede Compose;
- não há `down`, prune, remoção de volume, force push ou migration destrutiva.

## Plano de rollback

Publicar pelo fluxo protegido a configuração `WHATSAPP_PROVIDER=sandbox`, preservando outbox, auditoria e volumes Evolution. Se o schema Markina não tiver mudado, a automação pode restaurar somente o código ao SHA saudável; depois do início de migration, qualquer recuperação de banco é manual e exige aprovação. Os serviços/volumes Evolution permanecem preservados e sem porta pública para diagnóstico.

## Gates humanos restantes

1. aprovação explícita deste inventário e do deploy;
2. configuração segura de segredos exclusivos de homologação;
3. informação do número próprio e pareamento pelo proprietário, somente após o deploy saudável;
4. confirmação humana do OTP real e revisão visual autenticada.
