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

## Limitações e próximo passo

Esta validação comprova somente a saída sanitizada em ambiente local. O motivo da falha remota e o estado atual de `/etc/pyp-backup`, `/opt/pyp-backup-runtime`, unidades, destino e vínculo continuam desconhecidos. Após revisão, merge e CI verde, a nova SHA exige instalação protegida do wrapper atualizado e aprovação operacional própria; só então repetir `operation=inventory`. Nenhuma escrita no Drive, instalação do runtime, vínculo, ensaio, backup real ou ativação de timer está autorizada por esta validação.
