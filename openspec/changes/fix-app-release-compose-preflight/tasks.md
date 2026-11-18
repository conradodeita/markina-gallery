# Tasks

- [x] 1.1 Registrar o bloqueio observado, a causa no helper e o contrato de falha fechada neste proposal, design, delta spec e plano de tarefas.
- [x] 1.2 Atualizar os helpers API/web para retirar somente o overlay RAW aposentado e nomear o caminho de qualquer manifesto restante que esteja ausente.
- [x] 1.3 Adicionar regressões que impedem a volta da referência RAW nos helpers e verificam a mensagem de erro com caminho.
- [x] 1.4 Atualizar o pin do wrapper SSH versionado e a documentação operacional; preservar o helper facial e os outros gates.
- [x] 1.5 Executar testes focados, políticas do wrapper, OpenSpec estrito e revisão do diff; registrar os resultados antes do commit/push.
- [ ] 2.1 Após integração e CI verde, atualizar a cópia root-owned do wrapper pelo procedimento autorizado e registrar proprietário, modo e hash.
- [ ] 2.2 Reexecutar o preflight remoto somente-leitura para o SHA integrado; prosseguir ao release protegido apenas se todos os dados observados corresponderem ao plano.

## Evidência local — 18/11/2026

- `bash scripts/test_deploy_prod_app_services.sh`: 6 testes passaram; política API/web aprovada.
- `python scripts/test_deploy_prod_web_policy.py`: política web aprovada.
- Os três contratos finais de fingerprint, reconciliação e rejeição de SHA em `test_prod_release_state.py` passaram separadamente (**3/3**).
- `python scripts/test_production_release_workflow_policy.py`: `publication_candidate_ready=true`, `somente_api_web`; política aprovada.
- `openspec validate fix-app-release-compose-preflight --strict`, `git diff --check` e sintaxe Bash dos helpers/wrapper/testes passaram.
- O blob do helper API/web (`16be8f6f61fd8cef109f65c3cb466726e7465be8`) corresponde ao pin `APP_SCRIPT_BLOB_SHA` no wrapper versionado.
- A execução completa de `test_deploy_prod_web.sh` mostrou os casos capturados sem falha, mas a sessão do terminal encerrou antes do resumo agregado; o CI Linux ainda precisa confirmar a suíte completa.
- A cópia root-owned e o inventário remoto ainda não foram atualizados/repetidos; tasks 2.1 e 2.2 continuam pendentes.
