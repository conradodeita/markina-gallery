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
2. Executar `docker compose -p markina-gallery -f docker/docker-compose.yml config` com o arquivo de ambiente selecionado.
3. Construir e subir somente a Markina Gallery. O serviço `migrate` executa `alembic upgrade head` antes da API e do worker.
4. Criar o administrador inicial uma única vez com `docker compose -p markina-gallery -f docker/docker-compose.yml run --rm api python -m app.seed_admin`.
5. Configurar no Nginx Proxy Manager apenas o host `markina-homolog.duckdns.org` apontando para `127.0.0.1:8080`, com certificado HTTPS para esse host. Não editar hosts existentes.

## Smoke test

- `curl -fsS https://markina-homolog.duckdns.org/healthz`
- `curl -fsS https://markina-homolog.duckdns.org/api/health`
- Abrir a tela inicial e confirmar os contextos Cliente e Fotógrafo.
- Confirmar senha + TOTP do administrador inicial; o WhatsApp continua em sandbox e não envia mensagem real.
- Conferir `docker compose -p markina-gallery -f docker/docker-compose.yml ps` e os logs da Markina Gallery, sem exibir segredos.

## Rollback

Em caso de falha, usar somente a versão anterior conhecida da Markina Gallery com `docker compose -p markina-gallery -f docker/docker-compose.yml up -d`. Não executar `prune`, não alterar ClearBudget, Nginx Proxy Manager, Portainer ou seus recursos. Se a migration falhar, não expor o proxy e registrar o erro antes de qualquer nova tentativa.
