# Validação da reconciliação do baseline de produção

## Release confirmado

- A execução da main `44851414814` concluiu `success` no SHA `492c141cd998efc87ebde1ee81ea9101effb4f7c`. O job protegido `production-app-release` `136823783825` publicou somente API/web; os digests registrados foram API `sha256:c0aed86f943e63f51b832c063f25e418e2537bab6ee3546656f5c0b56ef6df4a` e web `sha256:d9dfa2dae3692688c93eebcb9daf9f988a48c9e4aa41ec391b276244ef88f7c6`, ambos saudáveis. `APP_ENV=production`, `FACIAL_PROCESSING_ENABLED=true`, Nginx em `127.0.0.1:8080`; sem migration, runtime de backup, escrita no Drive ou ativação de timer.
- Esse SHA é a última publicação API/web confirmada. O manifesto ainda apontava para `f18db9f`, uma base anterior.

## Falha após a PR #399

- A CI de main `44906609703`, no merge `24670d10ce1c35921922e7723bb5dfc3c75ea9fc`, classificou `release_scope=app` usando baseline `f18db9f`. Todos os gates de código passaram; somente `production-app-preflight` falhou.
- A etapa remota somente leitura retornou `SHA não é a main local aprovada; preparação necessária` e `deploy-prod-app-services: suporte não verificável; preparação autorizada necessária`. Não produziu fingerprint ou ID de imagem base. Artefato e handoff foram ignorados e `production-app-release` ficou `skipped`. Nenhuma mutação de produção ocorreu nesse run.

## Correção e validação

- O manifesto foi atualizado para `production_baseline_sha=492c141`; os pins de runtime e `expected_database_revision=20261113_0126` permaneceram inalterados.
- No candidato `cd2af15907707e12c7627686ca80d7258a36afbf`, o comando real do classificador (`--base 24670d10ce1c35921922e7723bb5dfc3c75ea9fc --target cd2af15907707e12c7627686ca80d7258a36afbf`) retornou `release_baseline_sha=492c141cd998efc87ebde1ee81ea9101effb4f7c` e `release_scope=none`. O delta de cinco caminhos não contém runtime API/web.
- `scripts/check_prod_app_release_scope.py --base 492c141... --target 24670d1...` retornou `app_release_ready=true / criterio=somente_api_web`.
- `scripts/test_classify_prod_release.py`: 16 testes aprovados. `scripts/test_prod_app_release_scope.py`: 30 testes aprovados. `scripts/test_production_release_workflow_policy.py`: `publication_candidate_ready=true / somente_api_web` e `production release workflow policy: ok`.
- `openspec validate enable-platform-backup-runtime --strict` e `git diff --check` passaram. A CI da PR #401 `44908236760` passou no SHA `cd2af15907707e12c7627686ca80d7258a36afbf`, incluindo OpenSpec, Gitleaks, qualidade/backend, frontend, imagens AMD64/ARM64, quatro shards backend e `homolog-inventory-policy`. Jobs de publicação foram ignorados por se tratar de PR.

## Limites

O baseline reconciliado não alinha `origin/main` no servidor, instala o wrapper do backup, gera fingerprint operacional, vincula a pasta, escreve no Drive nem instala/ativa serviço ou timer. A etapa protegida de preparação continua pendente de inventário atual e aprovação operacional específica.
