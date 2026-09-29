# Evidências de validação

## Validação local — 2026-09-29

- `C:\Program Files\Git\bin\bash.exe -n scripts/resume-homolog.sh` e `bash -n scripts/test_resume_homolog.sh`: aprovados.
- `bash scripts/test_resume_homolog.sh`: aprovado com Docker/Compose/HTTP simulados; confirmou serviços base, workers faciais condicionais, worker de prévia existente, recusa de container ausente, bloqueio de DB unhealthy, seleção estrita `up -d --no-deps --no-recreate`, espera dos quatro endpoints e propagação de falha HTTP.
- `python scripts/test_resume_homolog_policy.py`: aprovado; confirma projeto/raiz/arquivo Compose fixos, limites de serviços, ausência de `compose start`, execução de `migrate`, Alembic, limpeza Redis ou comandos globais e paridade do runbook com o script.
- `python scripts/test_assert_homolog_schema_head.py -v`: **4 testes aprovados**, cobrindo head único, revisão atrasada, múltiplos heads e ancestral ausente.
- `python scripts/assert_homolog_schema_head.py --directory backend/migrations/versions --revision 20260929_0069`: revisão compatível com o único head local `20260929_0069`.
- `python scripts/test_deploy_homolog_policy.py` e `bash scripts/test_deploy_homolog.sh`: aprovados; políticas de deploy, manutenção, rollout facial, produção facial e shell concluíram sem regressão.
- `openspec validate --strict --all --no-interactive`: **72/72 itens aprovados**, zero falhas.

## Inventário remoto somente-leitura — 2026-09-29 19:34 UTC

Host `132.145.193.169`, diretório `/opt/markina-gallery`, checkout limpo em `b4c320e75cbe`; `.env.homolog` presente (conteúdo não lido/exposto). O novo `scripts/resume-homolog.sh` ainda não está no host.

- Markina: API, web, worker geral, três workers faciais, preview-adjustment e nginx estavam saudáveis. PostgreSQL e Redis estavam saudáveis. O contêiner histórico `markina-gallery-migrate-1` estava parado com exit 255; nenhum comando foi executado nele nesta inspeção.
- Banco: revisão observada `20260929_0069`.
- Entrada: nginx Markina publicado somente em `127.0.0.1:8080`; host compartilhado usa 80/443. Domínio `https://markina-homolog.duckdns.org/`. `/healthz` e `/api/health` responderam HTTP 200 local e público.
- Evolution: contêiner ativo, zero restarts.
- Vizinhos Firefly, Nginx Proxy Manager e Portainer ativos; nenhum recurso de terceiros foi alterado.

## Plano e autorização do ensaio remoto

O inventário anterior foi somente-leitura. O proprietário autorizou integrar os PRs #115 e #116 em `develop`, acompanhar o deploy e executar o ensaio controlado com parada apenas dos oito contêineres de aplicação da Markina. Antes da parada, um novo inventário confirmou o checkout limpo no SHA `207ee3744078c1b81e19712f846003a32ae49542`, idêntico a `last-healthy.sha`, e o script publicado. PostgreSQL e Redis Markina, Evolution e seus serviços, Firefly, Nginx Proxy Manager e Portainer estavam ativos; revisão do banco `20260929_0069`; healthchecks local e público em `/healthz` e `/api/health` aprovados. O nginx Markina publicava somente `127.0.0.1:8080`; o proxy compartilhado ocupava 80/443 e o domínio era `https://markina-homolog.duckdns.org/`. O plano apresentado restringiu a parada aos oito serviços da aplicação, seguida de execução do script e verificação de saúde, schema e vizinhos, sem alterar banco, Evolution, volumes, proxy ou outros projetos.

## Publicação e ensaio real — 2026-09-29

- PR [#115](https://github.com/conradodeita/markina-gallery/pull/115) integrado em `develop` no SHA `ff680e411d0c04fd3ca82c1885204891f56451a9`; [workflow 36628097734](https://github.com/conradodeita/markina-gallery/actions/runs/36628097734) concluiu CI e deploy com sucesso. Inventário remoto posterior confirmou esse SHA, schema `20260929_0069`, serviços saudáveis e endpoints públicos HTTP 200.
- PR [#116](https://github.com/conradodeita/markina-gallery/pull/116) integrado em `develop` no SHA `207ee3744078c1b81e19712f846003a32ae49542`; [workflow 36630317371](https://github.com/conradodeita/markina-gallery/actions/runs/36630317371) concluiu backend, frontend, gitleaks, OpenSpec e deploy com sucesso. O servidor registrou o mesmo SHA em HEAD e `last-healthy.sha`, com checkout limpo.
- Após novo preflight e plano de impacto zero, `docker stop` recebeu somente `markina-gallery-api-1`, `markina-gallery-web-1`, `markina-gallery-worker-1`, `markina-gallery-face-search-worker-1`, `markina-gallery-face-index-worker-1`, `markina-gallery-face-maintenance-worker-1`, `markina-gallery-preview-adjustment-worker-1` e `markina-gallery-nginx-1`; os oito nomes retornaram com exit 0. DB, Redis e Evolution não entraram no comando.
- Em `/opt/markina-gallery`, `bash scripts/resume-homolog.sh --public-base-url https://markina-homolog.duckdns.org` retornou exit 0. Preflight confirmou schema `20260929_0069` compatível e lista exata de oito serviços; `docker compose up -d --no-deps --no-recreate` retomou os contêineres existentes. A saída final confirmou todos saudáveis e os quatro healthchecks locais/públicos HTTP 200, sem executar migration.
- Verificação independente posterior: oito serviços da aplicação, PostgreSQL e Redis saudáveis; banco ainda em `20260929_0069`; `/healthz` e `/api/health` públicos retornaram HTTP 200; SHA/`last-healthy.sha` inalterados e checkout remoto limpo. Evolution API, banco e Redis permaneceram ativos, com `RestartCount=0` para Evolution API. Firefly, Nginx Proxy Manager e Portainer permaneceram ativos. O contêiner histórico `markina-gallery-migrate-1` permaneceu parado em exit 255; nenhuma migration fez parte do ensaio.
