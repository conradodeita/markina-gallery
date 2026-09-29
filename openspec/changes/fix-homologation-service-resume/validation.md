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

## Plano e gate do ensaio remoto

Nenhum arquivo remoto foi escrito e nenhum serviço foi parado/iniciado durante o inventário. Para validar a recuperação real, a nova versão do script precisa primeiro estar no checkout aprovado do servidor pelo fluxo normal de release. Após autorização operacional específica e novo preflight, o ensaio parará somente os oito contêineres de aplicação enumerados no inventário, preservando DB, Redis, Evolution, nginx de terceiros, volumes e dados. Em seguida executará `bash scripts/resume-homolog.sh --public-base-url https://markina-homolog.duckdns.org` e confirmará saúde local/pública, revisão 0069 invariável, Evolution e vizinhos sem alterações. Não executará Alembic, `down`, prune, limpeza nem restauração de banco. Task 2.2 permanece pendente até essa aprovação e evidência; os testes locais não são apresentados como validação remota.
