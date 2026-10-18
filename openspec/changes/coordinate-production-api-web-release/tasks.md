# Tasks

## 1. Exclusão mútua dos fluxos

- [x] 1.1 Fazer `deploy-prod-app-services.sh` adquirir o lock comum somente em `release` e `rollback`, com recusa antes de mutações quando há concorrência ou tentativa web-only pendente; ampliar o teste do script API+web para proteger o contrato. Evidência: `bash scripts/test_deploy_prod_app_services.sh` passou com lock livre, lock ocupado e marcador `web-in-flight.sha`; `python scripts/test_production_release_workflow_policy.py` confirmou o hash do script fixado no wrapper.
- [x] 1.2 Preservar o lock e a recusa de `app-in-flight.sha` no fluxo web-only; validar contenda, estado pendente e compatibilidade com as regras de escopo do fluxo web-only. Evidência: `bash scripts/test_deploy_prod_web.sh` e `python scripts/test_deploy_prod_web_policy.py` passaram; a política confirma mesmo caminho de lock em ambos os fluxos e recusa nos dois sentidos.

## 2. Documentação e validação

- [x] 2.1 Atualizar os runbooks de API+web e web-only para documentar o caminho do lock, falha fechada e estado de tentativa pendente, preservando os gates, baseline, schema, portas, domínio e impacto já documentados. Evidência: `python scripts/test_production_release_workflow_policy.py` confirmou SHA-base, schema `20261017_0084`, porta `127.0.0.1:8080`, domínio e exclusão do worker OTP.
- [x] 2.2 Executar os testes de release API+web, web-only e políticas existentes, validar Bash e OpenSpec em modo estrito, revisar diff e registrar evidências sem executar ações de produção. Evidência: testes API+web, web-only, `test_prod_app_release_scope.py` e `test_prod_facial_release_gates.py` passaram; `openspec validate coordinate-production-api-web-release --strict`, `bash -n` e `git diff --check` passaram. Nenhum deploy, migration, operação de host ou mutação de dados foi executado.

## Workflow follow-up

- Sincronizar a spec principal e arquivar a change somente após revisão humana.
- Uma publicação real exige seguir o workflow protegido existente e inventário/aprovação operacional específicos do candidato; esta change não autoriza deploy.