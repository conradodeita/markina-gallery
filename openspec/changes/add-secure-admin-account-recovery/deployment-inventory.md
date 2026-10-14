# Inventário de deploy em homologação

Preparado em 2026-08-31 para a change `add-secure-admin-account-recovery`. A autorização humana para implementar, testar e publicar esta change foi registrada na conversa antes da execução.

## Revisões e estado anterior

- SHA candidato da implementação: `8ee1f95e1be178d21c05d4797ed22f27b2ac5e10`.
- Base `develop` antes da change: `2419ac8d046be8051366690edfa80e609f00b752`.
- Último workflow `CI` bem-sucedido da base: run `33446777797`.
- SHA funcional final integrado em `develop`: `b625c20d13d8ea3009c365b1a3d744be8b48bbc6` (PR `#23`).
- Workflow de publicação bem-sucedido: run `33459767662`, job `deploy-homolog` `99707581785`, concluído em 2026-09-01.

## Escopo exclusivo

- checkout remoto: `/opt/markina-gallery`;
- projeto/arquivo: `--env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml`;
- subdomínio existente: `markina-homolog.duckdns.org`;
- única porta publicada pela Markina no host: `127.0.0.1:8080`, atrás do proxy existente;
- serviços reconstruídos: `api`, `web`, `worker` e Nginx interno da Markina;
- serviços Evolution existentes só são verificados/iniciados quando o perfil já está ativo;
- volumes preservados: `pgdata`, `redisdata`, `media-source`, `media-derivatives`, `media-history`, `evolution-instances`, `evolution-pgdata` e `evolution-redisdata`;
- nenhum serviço, volume ou porta novo nesta change.

## Banco e impacto

- migration aditiva: `20260831_0032_admin_account_recovery`;
- cria somente `admin_security_challenge`, `admin_action_token`, `email_delivery` e `email_delivery_attempt`, com índices/constraints;
- não altera nem remove `admin_user`, credenciais, sessões, galerias, clientes, histórico comercial ou mídia;
- o workflow cria dump lógico exclusivo da Markina antes de iniciar Alembic;
- nenhum `down`, prune, remoção de volume, restore automático, force push ou alteração de terceiro.

## Configuração externa

A aplicação passa a reconhecer `EMAIL_PROVIDER`, `EMAIL_CREDENTIAL_ENV`, `EMAIL_PAYLOAD_ENCRYPTION_KEY`, `PUBLIC_APP_ORIGIN`, variáveis `SMTP_*` e controles `EMAIL_*`. O deploy de código não altera `docker/.env.homolog`, secrets do GitHub ou DNS. Na ausência de configuração humana completa, o e-mail permanece sandbox/indisponível em fail closed e nenhum envio externo ocorre.

## Verificação e rollback

O workflow SHALL exigir CI backend/frontend/OpenSpec/gitleaks verde, backup, Alembic em head, saúde dos containers e respostas `200` em `/healthz` e `/api/health`. A migration aditiva pode permanecer em eventual rollback de aplicação; depois que Alembic inicia, a automação bloqueia rollback automático até revisão humana. Qualquer restauração de banco ou downgrade exige nova autorização explícita.

## Resultado da publicação

- backup lógico exclusivo da Markina criado antes da migration;
- checkout remoto confirmado no SHA `b625c20d13d8ea3009c365b1a3d744be8b48bbc6`;
- Alembic avançou de `20260831_0031 (head)` para `20260831_0032 (head)`;
- `/healthz`: HTTP `200`, corpo `ok`;
- `/api/health`: HTTP `200`, corpo `{\"status\":\"ok\",\"service\":\"api\"}`;
- `/admin/reset-password` e `/admin/verify-email`: HTTP `200` e `Referrer-Policy: no-referrer`;
- nenhuma configuração SMTP/DNS foi aplicada: o envio real de e-mail continua bloqueado até intervenção humana específica.
