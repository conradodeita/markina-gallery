# Tasks

- [x] 1.1 Registrar o bloqueio observado, a causa no helper e o contrato de falha fechada neste proposal, design, delta spec e plano de tarefas.
- [x] 1.2 Atualizar os helpers API/web para retirar somente o overlay RAW aposentado e nomear o caminho de qualquer manifesto restante que esteja ausente.
- [x] 1.3 Adicionar regressões que impedem a volta da referência RAW nos helpers e verificam a mensagem de erro com caminho.
- [x] 1.4 Atualizar o pin do wrapper SSH versionado e a documentação operacional; preservar o helper facial e os outros gates.
- [x] 1.5 Executar testes focados, políticas do wrapper, OpenSpec estrito e revisão do diff; registrar os resultados antes do commit/push.
- [x] 2.1 Após integração e CI verde, atualizar a cópia root-owned do wrapper pelo procedimento autorizado e registrar proprietário, modo e hash.
- [x] 2.2 Preparar somente os objetos/ref de `main` no checkout remoto, sem trocar o checkout ativo, para tornar o SHA integrado verificável.
- [x] 2.3 Identificar a causa do segundo preflight bloqueado e inventariar somente o bloco Compose persistente, sua identidade e os containers Gemma, sem exibir valores de configuração.
- [x] 2.4 Implementar e testar uma reconciliação fail-closed e um dispatch de produção protegido que preserve backup, proprietário/modo e todos os bytes não relacionados do overlay.
- [x] 2.4.1 Tornar o snapshot de containers compatível com estados sem `Health`, incluir regressão com containers sintéticos com e sem healthcheck e registrar a causa do primeiro dispatch protegido.
- [ ] 2.5 Após CI verde e integração da reconciliação, executar o workflow protegido sob lock no host; validar Compose antes/depois e manter intactos o container Gemma parado e todos os outros containers.
- [ ] 2.6 Reexecutar o preflight somente-leitura para o SHA atual de `main`; prosseguir somente se fingerprint, identidade, hashes, versão, schema, saúde, ingress e flag facial corresponderem ao plano.
- [ ] 2.7 Executar o release protegido apenas de API/web, sem migrations, alteração de `.env`, reinício de workers ou instalação/ativação de backup.
- [ ] 2.8 Confirmar versão/image IDs de API/web, schema `20261113_0126`, saúde HTTPS, `APP_ENV=production`, `FACIAL_PROCESSING_ENABLED=true` e preservação dos serviços/dados fora do escopo.

## Evidência local — 18/11/2026

- `bash scripts/test_deploy_prod_app_services.sh`: 6 testes passaram; política API/web aprovada.
- `python scripts/test_deploy_prod_web_policy.py`: política web aprovada.
- Os três contratos finais de fingerprint, reconciliação e rejeição de SHA em `test_prod_release_state.py` passaram separadamente (**3/3**).
- `python scripts/test_production_release_workflow_policy.py`: `publication_candidate_ready=true`, `somente_api_web`; política aprovada.
- `openspec validate fix-app-release-compose-preflight --strict`, `git diff --check` e sintaxe Bash dos helpers/wrapper/testes passaram.
- O blob do helper API/web (`16be8f6f61fd8cef109f65c3cb466726e7465be8`) corresponde ao pin `APP_SCRIPT_BLOB_SHA` no wrapper versionado.
- A saída local agregada de `test_deploy_prod_web.sh` não foi registrada antes do encerramento do terminal; o CI Linux do PR #376 concluiu verde e validou a suíte correspondente no SHA publicado.

## Evidência operacional adicional — 18/11/2026

- A PR #376 foi integrada como `6d92ec203599f9cad35777e640186461b63d6da7`; CI do PR passou no run `44236805663`.
- Wrapper instalado pelo run `44243882449`, attempt 1: `root:root`, modo `0755`, SHA-256 `846c4519d9dd822086cf190939acb55f87040e950d68489def923e89269eb152`. A cópia anterior foi preservada em `/var/backups/markina-gallery/preflight-ssh-wrapper-20261118T055556Z-preview-migration-6d92ec203599` com SHA-256 `6dc6f5786cdce7dd924df3a1b7028eada10dee2aa878e3020607da32bad1c7c8`; o instalador confirmou recusa de comando arbitrário e não reiniciou serviços.
- A preparação remota buscou somente `origin/main`; o `HEAD` permaneceu em `bfe511f850224823254b0fc9f51fa7ff60ecfba0`, a árvore permaneceu limpa e o objeto alvo `6d92ec203599f9cad35777e640186461b63d6da7` ficou disponível. Nenhum serviço/container foi alterado.
- No run `44247817045`, attempt 1 falhou antes de inventariar porque faltava o objeto alvo; após a preparação, attempt 2 passou pelos gates de código, mas o preflight falhou em `docker compose config` ao resolver `face-gemma-index-worker` sem imagem/build. O release foi ignorado.
- Inventário SSH somente-leitura confirmou que o serviço não existe nos manifestos versionados; o estado persistente `/var/lib/markina-gallery/deploy-state/system-monitor.compose.yml` tem proprietário `ubuntu:ubuntu`, modo `0600`, 653 bytes e SHA-256 `c63599b84764f6141cf9860ce1a352f6e11eae55ea4c24b75959ca277c3cd60e`. O bloco Gemma tem somente as chaves `environment` e `SYSTEM_MONITOR_ENABLED`, sem `image` ou `build`; nenhum valor foi lido/exibido.
- `docker ps` somente-leitura confirmou zero containers Gemma em execução e um em qualquer estado. O container parado será preservado. A diretiva de backup poderá ser gravada com modo `0600` no `deploy-state` (`ubuntu:ubuntu`, diretório `0700`); `/var/backups/markina-gallery` é `root:root 0750` e não será usado pelo usuário SSH.
- Docker Compose local v5.7.0 reproduziu o erro com um bloco equivalente contendo somente `environment`, tanto sem perfil como com `--profile facial`; portanto, remover o perfil do helper não resolveria a causa. Não houve escrita no overlay de produção.
- A rotina `operations/reconcile_retired_gemma_stub.py --self-test` passou localmente em cinco casos; os dois testes POSIX de backup e substituição atômica foram ignorados neste Windows e serão executados no job `openspec` Linux do PR. Ruff, `ast.parse` e `git diff --check` passaram.
- `openspec validate fix-app-release-compose-preflight --strict` passou; `openspec validate --strict --all` passou **192/192**. `check_prod_app_release_scope.py --base bfe511f850224823254b0fc9f51fa7ff60ecfba0 --target HEAD` aprovou `somente_api_web`; `test_production_release_workflow_policy.py` passou.
- A PR #377, run CI `44263110039`, concluiu com sucesso. Os jobs `openspec`, `gitleaks`, `backend-quality`, os três shards de `backend-tests`, `frontend`, imagens AMD64/ARM64 e `homolog-inventory-policy` passaram. O job OpenSpec executou os sete testes do helper em Linux, incluindo backup exclusivo modo `0600` e substituição atômica com preservação de proprietário/modo; ambos também passaram.
- Próxima sequência: integrar a PR após CI verde; então disparar `app-compose-reconcile`, validar `config --quiet` e refazer o preflight oficial. Se a identidade mudar, houver container Gemma ativo ou Compose não validar, a operação aborta/recupera e não há deploy.

## Evidência da primeira execução protegida — 18/11/2026

- A PR #377 foi integrada em `main` como `aa9373cdf9c800ff825ee9d002f6e62a8552a61c`; o CI do PR concluiu verde no run `44267143827`.
- O push executou o preflight somente-leitura do run `44271279745`, que confirmou o bloqueio esperado no serviço `face-gemma-index-worker` sem imagem/build; o release foi ignorado.
- O dispatch `app-compose-reconcile` do run `44271496053` recebeu a aprovação padrão do ambiente protegido `production`, mas abortou antes da leitura ou escrita do overlay com `read_only_precondition_failed`.
- Diagnóstico SSH somente-leitura reproduziu a falha: o snapshot do Docker usa um template que acessa `.State.Health` em sete containers sem healthcheck. `docker inspect --format '{{json .State}}'` funcionou nos 43 containers e reportou sete sem `Health`.
- O checkout de produção permaneceu em `bfe511f850224823254b0fc9f51fa7ff60ecfba0`, `origin/main` correspondeu a `aa9373cdf9c800ff825ee9d002f6e62a8552a61c`, a API continuou saudável com `APP_ENV=production` e `FACIAL_PROCESSING_ENABLED=true`. O overlay permaneceu `ubuntu:ubuntu`, modo `0600`, 653 bytes, SHA-256 `c63599b84764f6141cf9860ce1a352f6e11eae55ea4c24b75959ca277c3cd60e`; nenhuma alteração ou backup de ensaio foi criado.
- O teste do helper passou **10/10** localmente; os dois testes POSIX de backup/substituição ficaram ignorados por esta estação Windows. Ruff, política do workflow, `openspec validate ... --strict`, validação global OpenSpec (**192/192**) e `git diff --check` passaram.
- O comando remoto somente-leitura `docker inspect --format '{{.Id}} {{json .State}}'` foi processado por Python em **43/43** containers, preservando ID/estado e representando ausência de healthcheck como `none`; sete containers não têm `Health`. Isso reproduziu o formato corrigido contra o runtime real sem alterar containers.
- Próximo passo: passar CI da correção, integrar e repetir o dispatch protegido. O preflight e o deploy continuam bloqueados até a reconciliação passar.
