# Tasks

## 1. Reconciliar a linha de release

- [x] 1.1 Registrar no manifesto app o SHA de produção confirmado `b4f15abd6a71585082758062feba7fcfcc225587` e a revisão observada `20261017_0084`; validar formato e ancestralidade em testes e manter o fluxo fechado se o alvo não descendê-los. Evidência: manifesto validado por regex; `git merge-base --is-ancestor` confirmou o SHA como ancestral de `origin/develop`; testes de manifesto e grafo Git incluídos em `scripts/test_classify_prod_release.py`.
- [x] 1.2 Alterar o classificador para usar esse baseline: sincronização até o SHA saudável retorna `none`, delta app descendente retorna `app`, e delta facial/misto/sem ancestralidade não seleciona release; verificar com `scripts/test_classify_prod_release.py` e regressões de política. Evidência: `python scripts/test_classify_prod_release.py -v` — 10 testes aprovados, incluindo app, facial, mixed, baseline não ancestral e delta só de documentação.
- [x] 1.3 Atualizar as instruções do classificador no workflow para que o PR de reconciliação de `main` com o SHA já ativo não dispare preflight ou deploy; verificar as condições por `scripts/test_production_release_workflow_policy.py`. Evidência: `python scripts/test_production_release_workflow_policy.py` passou; o step da CI nomeia a base saudável e os testes de classificador confirmam `none` na reconciliação sem runtime.

## 2. Permitir somente o delta revisado da aplicação

- [ ] 2.1 Expandir o manifesto e o verificador app para fixar os quatro runtimes da identificação de responsáveis por pastas privadas e aceitar somente testes, OpenSpec, documentação e arquivos operacionais listados; verificar positivos para os blobs exatos e negativos para workers, migration, Compose, facial e blobs divergentes com `python scripts/test_prod_app_release_scope.py`.
- [x] 2.2 Atualizar o script de release para exigir `20261017_0084`, sem migration, preservando o estado/fingerprint e recriando apenas `api` e `web`; adaptar `scripts/test_deploy_prod_app_services.sh` para cobrir schema esperado, schema divergente e confirmação de que nenhum worker é chamado. Evidência: teste Git Bash aprovado; sucesso simulado recriou apenas API/web, schema divergente abortou antes de alterar imagens/serviços e nenhum worker ou Alembic foi invocado.
- [x] 2.3 Ampliar o wrapper SSH versionado apenas com o comando de inventário app restrito e SHA completo; testar rejeição de comandos arbitrários e registrar no runbook a instalação/conferência separada da cópia root-owned. Evidência: `python scripts/test_production_release_workflow_policy.py` verificou os comandos app/rollback, o hash exato do script e a recusa de execução arbitrária; a cópia root-owned continua como gate operacional pendente.
- [x] 2.4 Atualizar `docs/DEPLOY-PROD-APP.md` e os testes de política com baseline, schema, escopo de runtime, portas/domínio, impacto da reinicialização e exclusão explícita do worker OTP; verificar os comandos e as afirmações com as políticas locais. Evidência: `python scripts/test_production_release_workflow_policy.py` aprovou assertions do SHA, revisão 0084, domínio, porta 8080 e exclusão do worker OTP; runbook registra possível interrupção e wrapper desatualizado.

## 3. Validar e preparar integração do código aprovado

- [x] 3.1 Executar testes de escopo/classificador, script simulado, política do workflow, validação OpenSpec estrita, revisão do diff e checks aplicáveis; registrar logs/resultados e corrigir falhas antes de abrir PR. Evidência local: classificador 10/10, app scope 4/4, simulação de release/rollback API-web aprovada (inclui schema divergente sem mutação), política do workflow aprovada, Ruff aprovado, `git diff --check` limpo e OpenSpec CLI 1.14.0 `validate --all --strict` com 111 aprovados/0 falhas.
- [ ] 3.2 Integrar localmente o gate e o commit original do recurso na PR #220, preservando o histórico de `main` e do SHA instalado; verificar ancestralidade sem force-push.
- [ ] 3.3 Conferir que a classificação e o gate app recebem o SHA instalado como base e aceitam somente o delta aprovado, sem migrations ou workers; verificar o candidato real e a reconciliação sem runtime por testes.
- [ ] 3.4 Retargetar a PR #220 para `main`, revisar o delta desde o runtime instalado e acompanhar CI completo antes da integração e do preflight protegido.

## 4. Executar gates de produção autorizados

- [ ] 4.1 Instalar/conferir a versão root-owned do wrapper somente pelo procedimento operacional autorizado; registrar owner, modo e hash. Se não houver acesso, manter o bloqueio e não contornar o wrapper.
- [ ] 4.2 Executar inventário somente-leitura no SHA exato integrado e apresentar ao proprietário host/projeto, SHA atual/alvo, revisão 0084, serviços, portas/subdomínio, fingerprint, impacto, validações e rollback; prosseguir somente após aprovação específica desse inventário.
- [ ] 4.3 Após aprovação protegida do Environment `production`, acompanhar o release, confirmar que apenas `api` e `web` foram recriados, que Alembic continua em `20261017_0084`, que o worker OTP não foi recriado e que os smoke tests passam; registrar evidência e bloqueios restantes.

## Workflow follow-up

- Sincronizar `deployment-operations` e arquivar a change somente após revisão humana e evidência da publicação, ou registrar o bloqueio operacional sem marcar tasks pendentes como concluídas.
