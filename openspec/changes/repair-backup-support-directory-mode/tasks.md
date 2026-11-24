# Tasks

## 1. Operação limitada no helper

- [ ] 1.1 Implementar `repair-support-backups-mode` no helper usando somente o diretório fixo, fingerprint atual e classificação exclusiva `target_mode_invalid`; cobrir alvo elegível, conteúdo-preservado e rejeição de diretório ausente/inseguro com testes POSIX sintéticos.
- [ ] 1.2 Implementar verificação por identidade do inode e falha fail-closed definida no design; cobrir divergência concorrente, falha de pós-verificação sem retry/limpeza e saída sanitizada com testes que confirmem ausência de caminho, metadados brutos e conteúdo.

## 2. Canal protegido e integração

- [x] 2.1 Adicionar a operação fixa ao workflow existente, exigindo fingerprint, `main` com CI verde e ambiente `production`; atualizar teste estático para rejeitar parâmetros arbitrários e confirmar que inventário/preparação não executam a correção, validando também o YAML.
- [x] 2.2 Executar testes focados do helper e do workflow, Ruff e `openspec validate repair-backup-support-directory-mode --strict`; revisar o diff contra código morto/duplicado na área afetada, executar `git diff --check` e registrar resultados e limitações em `validation.md`.

## 3. Gate de integração

- [ ] 3.1 Após revisão humana e integração autorizada, confirmar CI verde na `main` no SHA exato e registrar o run em `validation.md`; nenhuma operação remota é disparada por esta task.

## Gates pendentes

- As tasks 1.1 e 1.2 aguardam CI Linux para executar os testes POSIX que foram ignorados no Windows; a implementação e cobertura estão no diff local.
- A task 3.1 aguarda revisão humana, integração autorizada e CI verde da `main` no SHA exato.
- Após merge/CI, qualquer operação remota exige novo `support-inventory`, revisão da fingerprint atual, autorização operacional específica e aprovação do ambiente `production`; depois da correção, executar novo inventário antes de considerar `prepare-support`.
