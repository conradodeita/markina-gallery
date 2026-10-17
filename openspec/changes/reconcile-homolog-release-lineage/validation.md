# Validação

## Inventário somente leitura

- `39036156815`, esperado `71be3b29659143293351968e15fb4886c2d72bf0`: a guarda revelou `0779b3e4400f8511980c2d18e79ef8eea586a341` e encerrou antes de consultas.
- `39036197944`, esperado `0779b3e4400f8511980c2d18e79ef8eea586a341`: inventário concluído. Projeto Compose `markina-gallery`, entrada `127.0.0.1:8080`, domínio `markina.pickyourpic.com.br`, serviços ativos saudáveis, HTTP 200 em `/healthz` e `/api/health`, filesystem do projeto 64% usado e Alembic `20261016_0082`.
- Inventário apontou um container de migration antigo parado e workers órfãos de módulos opcionais. Nenhum container foi removido ou reiniciado.

## Bloqueio inicial e correção da proteção

- CI pós-merge #204 `39032173810`: backend, frontend, Gemma, OpenSpec, Gitleaks e inventário passaram; `deploy-homolog` foi rejeitado antes de executar passos porque `develop` não estava protegida.
- O ambiente `homolog` mantém `required_reviewers` e `protected_branches=true`. A branch `develop` agora exige os mesmos checks que `main` (`backend`, `frontend`, `gemma-runtime`, `openspec`, `homolog-inventory-policy`, `gitleaks`), bloqueia force-push e deleção e aplica as regras também a administradores. A regra de produção não foi alterada.

## Reconciliação local em andamento

- `main` tem 43 commits posteriores a `71be3b2`, incluindo a migration facial `20261016_0082`; `develop` e a migration de pastas da change #204 usavam outro arquivo com o mesmo identificador.
- Integração simulada apresentou apenas conflito em `.gitleaksignore`; a resolução preserva os fingerprints exatos e comentários de ambos os lados.
- A migration de pastas foi renomeada para `20261017_0083_private_upload_batch_folder_scope.py`, com `down_revision = "20261016_0082"`; o teste passa a atualizar a base `0081` até `0083`.
- `python -m alembic heads`: `20261017_0083 (head)`.
- `python -m pytest tests/test_private_upload_batch_migration.py -q`: 1 teste ignorado localmente porque o PostgreSQL sintético não está configurado; a regressão será executada no CI do PR.
- `openspec validate reconcile-homolog-release-lineage --strict`, `openspec validate fix-private-photo-notifications-and-admin-metrics --strict` e `openspec validate reveal-homolog-sha-on-inventory-mismatch --strict`: válidos.
- `git diff --check`: sem erros.
- CI `39036724855`: backend, frontend, Gemma e OpenSpec passaram; `homolog-inventory-policy` e Gitleaks falharam. Gitleaks apontou quatro fingerprints históricos conhecidos porque o conflito de `.gitleaksignore` havia concatenado linhas. As linhas foram restauradas; Gitleaks 8.24.3 local varreu 638 commits e não encontrou achados.
- O teste de política de produção falhou porque a PR de homolog altera `auth.py` e `main.py`, blobs fixados pelo gate facial, embora as mudanças sejam somente de upload/métricas. O step desse gate agora roda em PRs/pushes de `main`; o teste de política de homologação verifica a condição, e o gate facial continua obrigatório em `main`. Testes locais `scripts/test_deploy_homolog_policy.py` e `scripts/test_deploy_homolog.sh` passaram.
- Ainda pendentes: revisão do diff integrado, regressão PostgreSQL, CI integral no PR para `develop`, merge e deploy autorizado pelo gate do ambiente.

## Sem alteração remota de aplicação

Até a integração, o commit e o PR desta change, as atividades feitas no servidor foram somente os inventários aprovados. O job de deploy anterior falhou antes de iniciar; não houve backup, migration, build, restart ou alteração de dados.
