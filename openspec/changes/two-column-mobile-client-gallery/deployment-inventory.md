# Inventário de deploy em homologação

## Escopo

- Change: `two-column-mobile-client-gallery`
- Destino: `https://markina-homolog.duckdns.org`
- Branch de integração: `develop`, após pull request com CI verde
- Migration: nenhuma
- Backfill/reprocessamento: nenhum
- Alterações de runtime: frontend CSS e algoritmo de novas prévias protegidas

O SHA final será registrado após o merge. O deploy SHALL publicar exatamente esse SHA.

## Topologia preservada

- Projeto Compose: `markina-gallery`
- Entrada local do projeto: `127.0.0.1:8080`
- API interna: `8000`
- Web interna: `3000`
- PostgreSQL e Redis sem portas públicas
- Serviços: `nginx`, `web`, `api`, `worker`, `db`, `redis`, `face-index-worker`, `face-search-worker` e `face-maintenance-worker`; Evolution somente em seu estado já existente
- Volumes de banco, Redis, fontes, derivados, histórico e referências faciais preservados

## Impacto zero

- Não executar `docker compose down`, prune, remoção de volumes ou remoção automática de órfãos.
- Não alterar proxy, DNS, certificados, firewall, redes, containers, imagens ou volumes de terceiros.
- Não chamar o endpoint de proteção visual nem reenfileirar as `637` fotos existentes.
- Não executar migration ou operação destrutiva de banco.
- Manter `FACIAL_PROCESSING_ENABLED=true` e os workers faciais saudáveis.
- Executar o backup lógico exclusivo da Markina já exigido pela automação de deploy, ainda que esta entrega não altere schema.

## Verificação

1. CI: Ruff/pytest, ESLint/Vitest/build, OpenSpec e Gitleaks.
2. Deploy: SHA exato, backup, inventário pré/pós e healthchecks dos serviços.
3. Externo: `GET /healthz`, `GET /api/health` e página inicial com HTTP `200`.
4. Humano: roteiro em `homologation-checklist.md`.

## Rollback

Retornar somente os serviços Markina ao SHA saudável anterior pela automação versionada. Não há migration, backfill ou dado novo a desfazer; prévias novas criadas com texto único permanecem válidas. O acervo existente não é modificado por esta entrega.
