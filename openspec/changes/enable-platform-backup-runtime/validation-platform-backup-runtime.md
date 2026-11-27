# Validação local do runtime protegido de backup

> **EVIDÊNCIA HISTÓRICA — runtime próprio aposentado em 25/11/2026.** Os resultados abaixo pertencem ao código antigo. Os gates de instalar runtime, vincular destino, ensaiar com o Picker, fazer backup ou ativar timer não estão vigentes e não autorizam operação. O texto não comprova estado atual do servidor; a retirada de restos segue `retire-platform-backup-runtime` e a prova sintética vigente está em `prove-open-source-backup-and-recovery`.

**Data:** 20/11/2026
**Ambiente:** Windows, worktree `codex/record-picker-focus-release`
**Escopo:** artefato ARM64, inventário/fingerprint, instalador inerte, vínculo e ensaio sintético, canal protegido e allowlist do release API/web.

## Evidências locais

| Verificação | Resultado |
|---|---|
| `backend/tests/test_platform_backup_workspace_store.py` e `backend/tests/test_platform_backup_production_cli.py` | 26 passaram, 1 skip |
| Testes do artefato de runtime | 4 passaram |
| Testes do inventário | 5 passaram, 1 skip |
| Testes do instalador | 1 passou, 4 skips |
| Testes do workflow protegido | passou |
| `scripts/test_prod_app_release_scope.py` | 30 passaram |
| Ruff nos arquivos Python afetados | passou |
| `compileall` nos módulos Python afetados | passou |
| Parse YAML de `ci.yml` e dos dois workflows de backup | passou |
| `bash -n` do builder, instalador do wrapper e forced-command wrapper | passou |
| `openspec validate enable-platform-backup-runtime --strict` | passou |
| `git diff --check` | passou |

O teste de escopo usa repositórios Git temporários. Seu fixture remove os overrides externos `GIT_CONFIG_*` para que a configuração injetada pelo ambiente desktop não altere a interpretação do Git; a suíte completa passou após esse isolamento.

## CI remoto do candidato

A [CI `44845952777`](https://github.com/conradodeita/markina-gallery/actions/runs/44845952777) concluiu `success` para a PR #398 no SHA `7c4e6842d0bd97327c754b1c2d06102c554ad51a`. Passaram OpenSpec, escopo, Gitleaks, frontend, backend-quality, imagens AMD64/ARM64, os quatro shards do backend, `homolog-inventory-policy` e `gemma-runtime`. A política agregada instalou Ruff 0.17.6, aprovou os testes do artefato (4), do inventário executado com `sudo` (6) e do instalador executado com `sudo` (5), validou o canal protegido e montou/verificou o bundle no runner: `source_sha=4d6b17b12da5503abeef4a0625eb77fee29aa647`, `bundle_sha256=d715489b5e2836a8847e1803c84ad9ba791de8996401321542f86836fd943611`. O arquivo ficou no diretório temporário do runner; não foi publicado como release nem transferido ao servidor.

O ciclo de correção da CI encontrou e resolveu três incompatibilidades: o job agregado não preparava Ruff; o builder era chamado como executável apesar de estar versionado sem esse modo; e uma asserção global impedia o staging temporário recém-adicionado ao forced-command. O job de CI instala Ruff e chama o builder via Bash. O teste de política verifica SHA remoto antes do staging, limpeza via `trap`, ausência de temporários no caminho de preflight legado e ausência de `git fetch` no wrapper. A execução final passou esses gates; a workflow de operação protegida ainda continha uma invocação direta, descoberta no primeiro despacho real e registrada abaixo.

Os jobs de preflight e publicação protegidos ficaram ignorados por se tratar de uma PR. Nenhum inventário do host, SSH, wrapper/runtime, vínculo Drive, ensaio remoto, backup real ou timer foi executado.

## CI de push na main após o merge — 20/11/2026 BRT (21/11 UTC)

A [CI `44851414814`](https://github.com/conradodeita/markina-gallery/actions/runs/44851414814) foi disparada pelo push do merge `492c141cd998efc87ebde1ee81ea9101effb4f7c` da PR #398. Gitleaks, OpenSpec, escopo, frontend, backend-quality, imagens AMD64/ARM64, quatro shards e agregação de testes backend, `homolog-inventory-policy` e `gemma-runtime` concluíram `success`. O único job com falha foi `production-app-preflight`, na etapa remota de inventário somente leitura; a resposta foi `SHA não é a main local aprovada; preparação necessária` e `deploy-prod-app-services: suporte não verificável; preparação autorizada necessária`.

O preflight não produziu inventário, fingerprint de aprovação ou ID da imagem base API. Os jobs de artefato e handoff foram ignorados, assim como o release. Houve uma chamada SSH para o comando fixo de preflight somente leitura, mas nenhuma instalação do runtime/wrapper, vinculação ou escrita no Drive, backup real, migration ou ativação de serviço/timer. A resposta do host aponta que é necessária preparação autorizada; a causa operacional detalhada não foi confirmada. O inventário anterior não deve ser tratado como renovado por esta tentativa.

## Limites e gates pendentes

- As tasks de implementação e validação 3.2l, 3.2m e 3.2n estão concluídas com as evidências locais e de CI acima. A PR #398 foi integrada no merge `492c141cd998efc87ebde1ee81ea9101effb4f7c`.
- O gate pai 3.2 permanece aberto: a CI de push da main não obteve inventário ou fingerprint e a resposta remota exigiu preparação autorizada. Depois da preparação e de um preflight válido, será necessário usar despachos protegidos separados para inventariar, instalar o runtime inerte e, com reautorização recente do proprietário, vincular e realizar o ensaio sintético. Isso requer inventário/plano e autorização operacional próprios; `enabled=false` deve ser preservado.
- A validação não escreveu no Google Drive, não vinculou a pasta, não gerou backup real e não habilitou/iniciou serviço ou timer. A task 3.3 continua pendente de autorização específica para a primeira cópia real e de prova de recuperação.

## Regressão observada na primeira execução do inventário dedicado — 21/11/2026

A tentativa 2 da CI de push da main `44851414814` concluiu `success` no SHA `492c141cd998efc87ebde1ee81ea9101effb4f7c`; os gates de código, preflight API/web, artefato, handoff e release passaram. O job protegido `production-app-release` `136823783825` publicou somente API e web. Os digests esperados e ativos conferidos foram API `sha256:c0aed86f943e63f51b832c063f25e418e2537bab6ee3546656f5c0b56ef6df4a` e web `sha256:d9dfa2dae3692688c93eebcb9daf9f988a48c9e4aa41ec391b276244ef88f7c6`; ambos foram reportados saudáveis. O log manteve `APP_ENV=production` e `FACIAL_PROCESSING_ENABLED=true`. Após a publicação, uma verificação HTTP somente de leitura retornou 200 para `/` e `/api/health` em `https://markina.pickyourpic.com.br`.

O despacho somente de inventário `44899475963`, também no SHA `492c141cd998efc87ebde1ee81ea9101effb4f7c`, passou `code-evidence` e falhou em `runtime-artifact` antes do preflight SSH. `scripts/build_platform_backup_runtime.sh` consta no Git com modo `100644`, mas o shell da workflow executava o arquivo diretamente; o runner reportou `Permission denied` e exit code `126`. Portanto `preflight` e `operate` foram ignorados: não houve conexão SSH, inventário atual do runtime, alteração no host, escrita no Drive ou backup real nesta execução.

Foi adicionada regressão estática exigindo que a workflow chame o builder por `bash`. A regressão falhou antes da correção com `runtime_workflow_builder_not_invoked_through_bash`; depois da alteração da invocação, `python scripts/test_platform_backup_runtime_workflow.py` passou (`platform_backup_runtime_workflow=valid`). Também passaram `openspec validate enable-platform-backup-runtime --strict`, parse YAML do workflow e `git diff --check`. A CI da PR #399 `44900387252` concluiu `success` no SHA `492ee99811e6f05ea6afaa268056cbdda25b0eed`, incluindo Gitleaks, OpenSpec, qualidade backend (com a regressão), frontend, builds AMD64/ARM64, todos os shards backend e `homolog-inventory-policy`. A task 3.2o está validada; o inventário remoto continua pendente até revisão/merge autorizados e CI verde na main.
