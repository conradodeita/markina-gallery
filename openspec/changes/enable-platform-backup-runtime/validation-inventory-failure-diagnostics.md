# Validação do diagnóstico sanitizado do inventário

## Contexto

A execução `44918158058`, no SHA `816ee36371f4a6cdfa5d05b490b6b6071d3a6459`, concluiu os gates de CI e a construção ARM64. O preflight remoto falhou, sem fingerprint, e o script mostrou apenas `platform-backup-runtime: inventory failed`. Não há evidência para atribuir a falha a uma consulta específica nem para inferir o estado atual do runtime.

## Implementação

O inventariador agora expõe somente um código interno presente em allowlist ou uma categoria fixa (`inventory_io_failed`, `inventory_command_failed`, `inventory_error` ou `inventory_failed`). Texto de exceção, caminhos, stderr/stdout de subprocessos, configuração e credenciais permanecem ocultos. Falha continua sem fingerprint ou precondição aprovada.

O wrapper SSH protegido fixa o novo blob do inventariador. Seu pin e a lista de operações permitidas foram verificados pelos testes de workflow e escopo; não houve alteração em `runtime-gates.json`, porque esses scripts pertencem à lista explícita de operações permitidas e não ao conjunto `support_blobs`.

## Validação local

Executada no worktree limpo baseado na main `816ee36371f4a6cdfa5d05b490b6b6071d3a6459`, com Python `3.12.9`:

- `python scripts/test_platform_backup_runtime_inventory.py -v`: 8 testes concluídos, 1 skip por exigir POSIX/root, indisponível no Windows; os testes de código allowlisted e de não exposição de texto dinâmico passaram.
- `python scripts/test_platform_backup_runtime_workflow.py -v`: `platform_backup_runtime_workflow=valid`.
- `python scripts/test_prod_app_release_scope.py`: 30 testes passaram em 204,524 s.
- `python scripts/test_production_release_workflow_policy.py`: política aprovada; escopo de publicação restrito a API/web.
- Ruff nos dois arquivos Python alterados: passou.
- `bash -n scripts/production-preflight-ssh-wrapper.sh`: passou.
- `openspec validate enable-platform-backup-runtime --strict`: passou.
- `git diff --check`: passou.

## CI da mudança

A PR #402 foi validada no SHA `357aa006d9f1246af34e1a1f59a9a6bc8631efa7` pelo run [`44920211887`](https://github.com/conradodeita/markina-gallery/actions/runs/44920211887), concluído com `success`. Passaram os quatro shards da suíte backend, o job agregado, qualidade backend, frontend, imagens AMD64/ARM64, OpenSpec, escopo e gitleaks. Os gates de publicação da aplicação ficaram ignorados, conforme esperado para `release_scope=none`.

## Limitações e próximo passo

Esta validação comprova a saída sanitizada localmente e a integração pela CI. Após o merge e a instalação protegida em 21/11, o novo código foi executado no host pelo modo read-only `inventory`, mas ainda não produziu fingerprint. O código `container_inventory_invalid` localiza uma validação de registro fixo API/web/db sem discriminar o papel ou campo; o motivo específico e o estado atual de `/etc/pyp-backup`, `/opt/pyp-backup-runtime`, unidades, destino e vínculo permanecem desconhecidos. A granularidade adicional é acompanhada na subtask 3.2r. Nenhuma escrita no Drive, instalação do runtime, vínculo, ensaio, backup real ou ativação de timer ocorreu.

## Resultado no host após atualização protegida

A PR #402 foi integrada como `33e2a95a8587835501518387106deae194152706`; a CI da main `44925165973` passou. A instalação protegida da ponte/wrapper `44935123431` passou, preservou o wrapper anterior e confirmou `containers_unchanged=true`. O inventory somente de leitura `44935370437` usou o código atualizado e retornou `container_inventory_invalid`; nenhuma fingerprint ou inventário foi produzido e `operate` foi ignorado. A categoria aponta para a validação do registro fixo de um dos containers da aplicação, mas a classificação atual não indica papel ou campo. Não executar inventário por SSH ad hoc; a precisão adicional será implementada em 3.2r.
