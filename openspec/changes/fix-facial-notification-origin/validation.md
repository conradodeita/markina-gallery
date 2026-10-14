## Evidências locais — 2026-09-22

- `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_facial_notification_origin.py backend/tests/test_facial_search_worker.py -q`: 101 testes passaram em 74,84 s. Inclui 86 casos iniciais de origem e 15 casos do worker.
- Após acrescentar a regressão da configuração Compose: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_facial_notification_origin.py -q`: 91 testes passaram em 10,59 s.
- `backend/.venv/Scripts/ruff.exe check backend/app backend/tests`: passou.
- `backend/.venv/Scripts/python.exe scripts/test_deploy_homolog_policy.py`: passou.
- `docker compose -p markina-gallery -f docker/docker-compose.yml --env-file <arquivo temporário vazio> --profile '*' config --format json`: configuração resolvida com valores sintéticos, confirmando `PUBLIC_APP_ORIGIN=https://markina-homolog.example` na API, worker geral e três workers faciais, mesmo com a URL legada local. Saída capturada sem exibir variáveis/segredos. Nenhum container iniciado ou alterado.
- `npx --offline @fission-ai/openspec@1.10.0 validate --strict --all --no-interactive`: 58 itens passaram, zero falhas.
- `git diff --check` restrito à alteração: passou. Revisão do diff confirma mudança apenas na resolução da origem, repasse no Compose, testes e artefatos desta change.

## Cobertura e limites

Os testes verificam prioridade da origem canônica, compatibilidade legada, recusa de origem principal inválida sem fallback, esquema/host/porta inválidos, endereços locais/privados IPv4 e IPv6, preservação do desenvolvimento local, texto completo da mensagem, envio único e ausência de chamada ao provedor quando a origem é inválida. PyYAML usado para resolver as âncoras do Compose já integra as dependências de `uvicorn[standard]`.

Sem alterações de frontend; build e typecheck frontend não se aplicam. Validação backend direcionada ao worker e notificações; a suíte completa será executada pelo CI do PR. Testes somente com dados sintéticos/provedor falso; nenhuma mensagem real enviada.

## Continuidade e entrega

Branch `feature/fix-facial-notification-origin`, baseada em `origin/develop` no commit `68a34f8840882bc3425e13865385043dabebb938`. Publicar PR para `develop` e parar imediatamente, aguardando o usuário confirmar CI verde. Não realizar merge, deploy, edição de `.env`, reenvio de mensagens antigas ou mudanças no servidor nesta etapa. Sincronização da spec consolidada e arquivamento aguardam revisão humana.

A aplicação em homologação depende da publicação posterior pelo workflow existente, que já configura a origem canônica e recria os serviços. Antes dessa operação, conferir inventário e apresentar impacto conforme o mandato. Mudanças locais de outras changes e `.codex-tmp/` permanecem fora do commit.
