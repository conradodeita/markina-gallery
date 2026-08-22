# docker — Orquestração do PhotoCRM

Projeto Compose exclusivo: **photocrm**. Use sempre o par explícito de flags:

```bash
docker compose -p photocrm -f docker/docker-compose.yml <comando>
```

- Única porta publicada no host: Nginx em `${PHOTOCRM_PORT:-8080}` (configurável via `docker/.env`).
- `db` (PostgreSQL 17) e `redis` (Redis 7) **não publicam portas** — apenas rede interna `photocrm_internal`.
- Volumes: `photocrm_pgdata`, `photocrm_redisdata`.

Subir: `docker compose -p photocrm -f docker/docker-compose.yml up -d --build`
Verificar: `docker compose -p photocrm -f docker/docker-compose.yml ps`
Parar (somente o PhotoCRM): `docker compose -p photocrm -f docker/docker-compose.yml down`

> ⚠️ **Máquina/servidor compartilhados:** outros projetos Docker podem estar em execução
> (ex.: `firefly_telegram`, que ocupa a porta 3000 no host). Nunca use `docker compose down`
> sem o par `-p photocrm -f docker/docker-compose.yml`, nunca use prunes, e se a porta
> `${PHOTOCRM_PORT}` estiver ocupada, escolha outra no `docker/.env` — sem tocar no outro projeto.
> O PhotoCRM não publica 3000/8000/5432/6379 no host, evitando conflito por padrão.
