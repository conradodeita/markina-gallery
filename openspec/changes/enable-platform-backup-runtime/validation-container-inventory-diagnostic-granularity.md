# Validação da granularidade sanitizada do inventário de containers

## Evidência que motivou a subtask

Após o merge da PR #402, a ponte e o wrapper foram atualizados pelo canal protegido no run `44935123431`, com `containers_unchanged=true`. O inventory read-only `44935370437` falhou com `container_inventory_invalid`; não emitiu fingerprint e `operate` foi ignorado. A categoria atual localiza a validação de um registro fixo API/web/db, mas não distingue papel ou campo. O teste de caracterização reproduziu essa saída genérica antes da alteração.

## Mudança e limite de dados

O inventariador passa a usar códigos estáticos allowlisted que identificam somente o papel fixo (`api`, `web` ou `db`) e a classe de validação (formato, ID, imagem, labels, estado, saúde ou início). Não registra valores observados, nomes/IDs de containers, argumentos/saídas do Docker, exceções ou caminhos. Papel ou classe desconhecidos continuam no código genérico seguro `container_inventory_invalid`. A fingerprint e as precondições continuam ausentes em qualquer falha.

## Validação local

Executada na branch `codex/backup-inventory-container-diagnostics`, baseada na main `33e2a95a8587835501518387106deae194152706`:

- Regressão sintética: 27 combinações (3 papéis × 9 classes) falharam antes com o código genérico e passaram depois com a classe estática correta.
- `python scripts/test_platform_backup_runtime_inventory.py -v`: 10 testes passaram; 1 teste root-only foi ignorado no Windows.
- `python scripts/test_platform_backup_runtime_workflow.py -v`: `platform_backup_runtime_workflow=valid`.
- `python scripts/test_prod_app_release_scope.py`: 30 testes passaram em 265,138 s.
- `python scripts/test_production_release_workflow_policy.py`: `production release workflow policy: ok`.
- Ruff nos dois arquivos Python alterados, sintaxe shell por Git Bash, OpenSpec estrito e `git diff --check`: passaram.
- O pin atualizado do inventariador coincide com o blob `b86f629a7117660334cbe66a86e6eb7aeb315298`.

## Limitações e próximo passo

CI da PR, merge e instalação protegida para a nova SHA ainda são gates pendentes. Após a instalação autorizada, repetir somente `operation=inventory` e usar o código estático para restringir a investigação. Não executar SSH ad hoc, instalar o runtime, vincular a pasta, fazer ensaio, iniciar backup real ou ativar timer com base nesta validação.
