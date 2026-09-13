# Inventário de deploy em homologação

## Estado candidato

- Change: `clarify-facial-consent-and-mobile-dialog`.
- Branch planejada: `feature/clarify-facial-consent-mobile-dialog`.
- Base saudável atualmente publicada: `78134395021b579a7e7df7a0597ce50d94b802c0`.
- Destino: `https://markina-homolog.duckdns.org`.
- Alteração funcional: somente texto, marcação acessível e CSS responsivo do diálogo de consentimento facial da cliente.
- Banco/migration: nenhuma alteração de schema, migration, backfill ou dados.
- Biometria: nenhum novo processamento, retenção, endpoint, modelo, índice ou gate; os prazos efetivos continuam fornecidos pelo backend.

## Topologia preservada

- Projeto/arquivo: `--env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml`.
- Checkout remoto exclusivo: `/opt/markina-gallery`.
- Entrada publicada: `127.0.0.1:8080`, atrás de `markina-homolog.duckdns.org`; `web:3000` e `api:8000` permanecem internos.
- PostgreSQL, Redis e workers permanecem sem portas públicas.
- O workflow preserva `FACIAL_PROCESSING_ENABLED=true` e `FACIAL_MAX_REFERENCE_BYTES=31457280`.
- Nenhum recurso de terceiro — proxy, DNS, certificado, firewall, rede, volume, container ou imagem — será alterado.

## Impacto zero e validação

- Não executar `docker compose down`, prune, remoção de volume, restore, downgrade nem manutenção destrutiva.
- Publicar somente o SHA integrado em `develop` pelo workflow CI existente.
- Validação local cirúrgica: 10 testes do componente facial, ESLint direcionado, TypeScript, OpenSpec estrito e `git diff --check` aprovados; suíte completa não executada por decisão humana explícita.
- Os gates obrigatórios do CI continuam ativos antes do merge e deploy.
- Após a publicação, confirmar SHA, migration inalterada em `20260910_0053 (head)`, serviços Markina saudáveis, flag facial preservada e HTTP `200` em `/healthz` e `/api/health`.
- Validar o diálogo em viewport mobile autenticada sem enviar nova referência facial.

## Rollback

Se houver regressão, retornar somente os componentes da Markina Gallery ao SHA saudável `78134395021b579a7e7df7a0597ce50d94b802c0`. Não executar downgrade, restore ou mutação de dados; repetir healthchecks e registrar o resultado.

## Autorização

- Push, merge e deploy desta change em homologação foram autorizados explicitamente pelo proprietário em 2026-09-13.
