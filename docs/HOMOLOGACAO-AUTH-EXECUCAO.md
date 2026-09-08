# Execução segura da homologação de autenticação

Este procedimento é exclusivo da Markina Gallery. Ele só pode começar depois da aprovação registrada no inventário e deve usar sempre `-p markina-gallery -f docker/docker-compose.yml`.

## Variáveis externas obrigatórias

Crie `/opt/markina-gallery/docker/.env.homolog` fora do Git, com permissões restritas. Use valores novos, próprios de homologação, para:

- `APP_ENV=staging`
- `DOMAIN=markina-homolog.duckdns.org`
- `MARKINA_GALLERY_PORT=127.0.0.1:8080`
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` e `DATABASE_URL`
- `SECRET_KEY` e `SESSION_COOKIE_NAME`
- `ADMIN_SEED_EMAIL`, `ADMIN_SEED_PASSWORD` (mínimo 12 caracteres) e `ADMIN_SEED_TOTP_SECRET`

Não copie banco, senha, TOTP, token DuckDNS, token WhatsApp ou segredo de produção. PostgreSQL e Redis ficam apenas na rede interna do Compose.

## Sequência de homologação

1. Confirmar que o diretório de destino e o arquivo `.env.homolog` pertencem ao serviço da Markina Gallery e não são legíveis por outros usuários.
2. Executar `docker compose --env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml config`.
3. Construir e subir somente a Markina Gallery. O serviço `migrate` executa `alembic upgrade head` antes da API e do worker.
4. Criar o administrador inicial uma única vez com `docker compose --env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml --profile bootstrap run --rm seed-admin`. A senha e o TOTP ficam disponíveis apenas durante esse container temporário, nunca na API em execução.
5. Conectar somente o serviço `nginx` da Markina à rede externa `npm-network`, sob o alias `markina-homolog-nginx`. Configurar no Nginx Proxy Manager apenas o host `markina-homolog.duckdns.org` apontando para `markina-homolog-nginx:80`, com certificado HTTPS para esse host. Não editar hosts existentes nem conectar serviços da Markina à rede do ClearBudget.

## Smoke test

- `curl -fsS https://markina-homolog.duckdns.org/healthz`
- `curl -fsS https://markina-homolog.duckdns.org/api/health`
- Abrir a tela inicial e confirmar os contextos Cliente e Fotógrafo.
- Confirmar senha + TOTP do administrador inicial; o WhatsApp continua em sandbox e não envia mensagem real.
- Conferir `docker compose -p markina-gallery -f docker/docker-compose.yml ps` e os logs da Markina Gallery, sem exibir segredos.
- Após o smoke test aprovado, remover qualquer arquivo temporário de credenciais iniciais, mantendo somente o `.env.homolog` protegido para a operação do ambiente.

## Rollback

Em caso de falha, usar somente a versão anterior conhecida da Markina Gallery com `docker compose -p markina-gallery -f docker/docker-compose.yml up -d`. Não executar `prune`, não alterar ClearBudget, Nginx Proxy Manager, Portainer ou seus recursos. Se a migration falhar, não expor o proxy e registrar o erro antes de qualquer nova tentativa.
