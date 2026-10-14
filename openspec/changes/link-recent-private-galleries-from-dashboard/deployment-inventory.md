# Inventário de entrega em homologação

## Estado candidato

- Change: `link-recent-private-galleries-from-dashboard`.
- Branch: `feature/link-recent-private-galleries-dashboard`.
- Base saudável publicada: `ba9457d1210277807c340084d4b37a9e9ee8ef14`.
- Destino eventual: `https://markina-homolog.duckdns.org`.
- Alteração funcional: somente o nome de cada galeria privada recente na Visão geral passa a abrir sua ficha administrativa pelo UUID opaco já retornado.
- Banco/migration: nenhuma alteração de schema, migration, backfill ou dados.
- Backend/API: nenhum endpoint, payload, consulta ou autorização alterado.

## Topologia preservada

- Projeto/arquivo: `--env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml`.
- Checkout remoto exclusivo: `/opt/markina-gallery`.
- Entrada publicada: `127.0.0.1:8080`, atrás de `markina-homolog.duckdns.org`; `web:3000` e `api:8000` permanecem internos.
- PostgreSQL, Redis e workers permanecem sem portas públicas.
- Nenhum recurso de terceiro — proxy, DNS, certificado, firewall, rede, volume, container ou imagem — será alterado.
- `FACIAL_PROCESSING_ENABLED=true` e os limites faciais vigentes deverão permanecer preservados.

## Impacto zero e validação

- Não executar `docker compose down`, prune, remoção de volume, restore, downgrade nem manutenção destrutiva.
- Publicar somente o SHA integrado em `develop` pelo workflow CI existente, após autorização humana explícita para merge/deploy.
- Validação local cirúrgica: 6/6 testes do painel, ESLint direcionado, TypeScript, OpenSpec estrito e `git diff --check` aprovados; suíte completa local não executada.
- Os gates obrigatórios do CI permanecem ativos no PR.
- Após eventual publicação, confirmar SHA, migration inalterada, serviços Markina saudáveis e HTTP `200` em `/healthz` e `/api/health`.
- A autenticação e a autorização continuam decididas pelo backend; o link apenas reutiliza a rota administrativa existente.

## Rollback

Em caso de regressão, retornar somente os componentes da Markina Gallery ao SHA saudável `ba9457d1210277807c340084d4b37a9e9ee8ef14`. Não executar downgrade, restore nem qualquer mutação de dados; repetir os healthchecks.

## Autorizações

- A implementação local da change foi solicitada explicitamente pelo proprietário em 2026-09-13.
- Merge e deploy desta change ainda exigem autorização humana explícita.
