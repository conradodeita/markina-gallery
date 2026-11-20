# Validação local do runtime protegido de backup

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

## Limites e gates pendentes

- Os cinco skips locais são as verificações root/POSIX: um teste de recibos root-only do inventário e quatro testes transacionais do instalador dependentes de `flock`/systemd. A CI executa os testes de inventário e instalação com `sudo`; essa evidência ainda depende do SHA final.
- A validação local não instalou wrapper ou runtime no servidor, não escreveu no Google Drive, não vinculou a pasta, não gerou backup real e não habilitou/iniciou serviço ou timer.
- O CI do SHA final e a revisão humana ainda não foram concluídos. As tasks 3.2l, 3.2m e 3.2n permanecem abertas até suas evidências correspondentes.
