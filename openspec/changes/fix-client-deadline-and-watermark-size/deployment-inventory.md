# Inventário de deploy em homologação

## Estado candidato

- Change: `fix-client-deadline-and-watermark-size`.
- Branch local: `feature/fix-client-deadline-watermark-size`.
- Base `develop` e SHA saudável atualmente publicado: `575032a1e199552318f61998c7942ede78c36846`.
- SHA funcional validado: `3e6bf8931d190a7f2e7b296c88e47b519d63421b`.
- Destino proposto: `https://markina-homolog.duckdns.org`.
- Alteração de runtime: somente frontend `web`; o backend recebeu apenas asserções de teste sobre o contrato já implementado.
- Banco/migration: nenhuma alteração; não há escrita, backfill ou transformação de dados existentes.
- Mídia: nenhum reprocessamento, alteração de derivados, jobs ou mudança em `backend/app/media.py`.

## Topologia preservada

- Projeto/arquivo: `--env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml`.
- Checkout remoto exclusivo: `/opt/markina-gallery`.
- Entrada publicada: `127.0.0.1:8080` atrás de `markina-homolog.duckdns.org`; `web:3000` e `api:8000` permanecem somente na rede interna.
- PostgreSQL, Redis e workers faciais permanecem sem portas públicas.
- O workflow SHALL preservar `FACIAL_PROCESSING_ENABLED=true` e `FACIAL_MAX_REFERENCE_BYTES=31457280`.
- Nenhum proxy, DNS, certificado, firewall, rede, volume, container ou imagem de terceiro será alterado.

## Impacto zero e validação

- Não executar `docker compose down`, prune, remoção de volume, restore, downgrade ou manutenção destrutiva.
- Publicar somente o SHA integrado em `develop` pelo workflow CI já existente.
- Confirmar migration inalterada em `20260910_0053 (head)`, containers Markina saudáveis e HTTP `200` em `/healthz`, `/api/health` e na entrada pública.
- Validação local cirúrgica: frontend `3 files/38 passed`; backend `1 passed`; TypeScript, Ruff, ESLint focado, OpenSpec estrito e `git diff --check` aprovados.
- A suíte completa e o ensaio de escalabilidade não foram executados localmente, conforme solicitação do proprietário; os gates obrigatórios do CI permanecem ativos antes do merge/deploy.

## Rollback

Se a aplicação falhar, retornar somente a aplicação Markina ao SHA saudável `575032a1e199552318f61998c7942ede78c36846`. Não executar downgrade, restore, limpeza ou mutação de dados; repetir healthchecks e registrar a ocorrência.

## Autorização

- Push, merge e deploy desta change em homologação foram autorizados explicitamente pelo proprietário em 2026-09-11, após a apresentação deste inventário.
