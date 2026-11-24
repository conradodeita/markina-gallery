# Tasks

## 1. Operação limitada no helper

- [x] 1.1 Implementar `repair-support-backups-mode` no helper usando somente o diretório fixo, fingerprint atual e classificação exclusiva `target_mode_invalid`; cobrir alvo elegível, conteúdo-preservado e rejeição de diretório ausente/inseguro com testes POSIX sintéticos. Validado em Linux na CI PR #425, run `45449415944`, SHA `7a509abf743c4a76b5719ff68033e52dc8268227`.
- [x] 1.2 Implementar verificação por identidade do inode e falha fail-closed definida no design; cobrir divergência concorrente, falha de pós-verificação sem retry/limpeza e saída sanitizada com testes que confirmem ausência de caminho, metadados brutos e conteúdo. `test_backup_mode_repair_fails_closed_if_path_identity_changes_after_chmod` e `test_repair_postcheck_failure_is_terminal_and_sanitized` passaram no mesmo run Linux.

## 2. Canal protegido e integração

- [x] 2.1 Adicionar a operação fixa ao workflow existente, exigindo fingerprint, `main` com CI verde e ambiente `production`; atualizar teste estático para rejeitar parâmetros arbitrários e confirmar que inventário/preparação não executam a correção, validando também o YAML.
- [x] 2.2 Executar testes focados do helper e do workflow, Ruff e `openspec validate repair-backup-support-directory-mode --strict`; revisar o diff contra código morto/duplicado na área afetada, executar `git diff --check` e registrar resultados e limitações em `validation.md`.

## 3. Gate de integração

- [x] 3.1 Após revisão humana e integração autorizada, confirmar CI verde na `main` no SHA exato e registrar o run em `validation.md`; nenhuma operação remota é disparada por esta task. PR #425 integrada em `e8b36204d9467914cfc9da90b5dcaabda087998a`; CI da `main` `45458633617` passou no mesmo SHA.

## Gates operacionais posteriores

- A CI Linux PR #425 run `45449415944` confirmou as tasks 1.1 e 1.2: ambos os testes POSIX (`test_backup_mode_repair_preserves_directory_identity_and_contents` e `test_backup_mode_repair_fails_closed_if_path_identity_changes_after_chmod`) passaram; o gate `homolog-inventory-policy` e o agregado legado `gemma-runtime` também passaram.
- Esta change não despachou operação remota. Qualquer execução futura exige novo `support-inventory`, revisão da fingerprint atual, autorização operacional específica e aprovação do ambiente `production`; depois da correção, é obrigatório executar outro inventário antes de considerar `prepare-support`.
