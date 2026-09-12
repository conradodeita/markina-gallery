# Inventário de deploy em homologação

## Estado candidato

- Change: `auto-enable-facial-processing-for-new-galleries`.
- Branch local: `feature/auto-enable-facial-processing-new-galleries`.
- Base e SHA saudável atualmente publicado em homologação: `3b4a759cbb32843059e62de56867a7a1ee8fd83b`.
- SHA funcional validado: `670996d6add228253373b12ffcd0b54036f07120`.
- Destino proposto: `https://markina-homolog.duckdns.org`.
- Alteração de runtime: resolução backend compartilhada por API e workers faciais; frontend não foi alterado.
- Banco/migration: nenhuma alteração de schema, backfill, escrita em massa ou transformação de dados.
- Mídia: nenhum upload, reprocessamento automático, derivado, duplicação ou exclusão.

## Comportamento e escopo

- Galeria ativa sem rollout persistido em ambiente algum passa a usar a disponibilidade geral `active/general` quando flag e calibração permitem.
- Rollout explícito `prepared`, `suspended` ou `revoked` continua bloqueando a galeria.
- Rollout explícito de outro ambiente falha fechado e não é contornado.
- Rollout explícito `active` continua exigindo etapa ativa e versões compatíveis.
- A alteração vale por leitura para galerias novas e existentes; não cria registros implícitos no banco.

## Topologia preservada

- Projeto/arquivo: `--env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml`.
- Checkout remoto exclusivo: `/opt/markina-gallery`.
- Entrada publicada: `127.0.0.1:8080` atrás de `markina-homolog.duckdns.org`; `web:3000` e `api:8000` permanecem internos.
- PostgreSQL, Redis e workers permanecem sem portas públicas.
- O workflow SHALL preservar `FACIAL_PROCESSING_ENABLED=true` e `FACIAL_MAX_REFERENCE_BYTES=31457280`.
- Nenhum proxy, DNS, certificado, firewall, rede, volume, container ou imagem de terceiro será alterado.

## Impacto zero e validação

- Não executar `docker compose down`, prune, remoção de volume, restore, downgrade ou manutenção destrutiva.
- Publicar somente o SHA integrado em `develop` pelo workflow CI existente.
- Validação local focada: 33 testes de rollout, status, indexação e busca aprovados; Ruff, OpenSpec estrito e `git diff --check` aprovados.
- Os gates completos obrigatórios do CI permanecem ativos antes do merge e do deploy.
- Após a publicação, confirmar SHA, migration inalterada em `20260910_0053 (head)`, containers Markina saudáveis, flags faciais preservadas e HTTP `200` em `/healthz`, `/api/health` e entrada pública.

## Rollback

Se a aplicação falhar, retornar somente os componentes Markina ao SHA saudável `3b4a759cbb32843059e62de56867a7a1ee8fd83b`. Não executar downgrade, restore, limpeza ou mutação de dados; repetir healthchecks e registrar a ocorrência.

## Autorização

- Push, merge e deploy desta change aguardam autorização humana específica após a apresentação deste inventário.
