# docker — Orquestração da Markina Gallery

Projeto Compose exclusivo: **markina-gallery**. Use sempre o par explícito de flags:

```bash
docker compose -p markina-gallery -f docker/docker-compose.yml <comando>
```

- Única porta publicada no host: Nginx em `${MARKINA_GALLERY_PORT:-8080}` (configurável via `docker/.env`).
- `db` (PostgreSQL 17) e `redis` (Redis 7) **não publicam portas** — apenas rede interna `markina-gallery_internal`.
- Volumes: `markina-gallery_pgdata`, `markina-gallery_redisdata`.

Subir: `docker compose -p markina-gallery -f docker/docker-compose.yml up -d --build`
Verificar: `docker compose -p markina-gallery -f docker/docker-compose.yml ps`
Parar (somente a Markina Gallery): `docker compose -p markina-gallery -f docker/docker-compose.yml down`

> ⚠️ **Máquina/servidor compartilhados:** outros projetos Docker podem estar em execução
> (ex.: `firefly_telegram`, que ocupa a porta 3000 no host). Nunca use `docker compose down`
> sem o par `-p markina-gallery -f docker/docker-compose.yml`, nunca use prunes, e se a porta
> `${MARKINA_GALLERY_PORT}` estiver ocupada, escolha outra no `docker/.env` — sem tocar no outro projeto.
> A Markina Gallery não publica 3000/8000/5432/6379 no host, evitando conflito por padrão.
