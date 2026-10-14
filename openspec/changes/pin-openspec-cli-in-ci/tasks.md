# Tasks

## 1. Fixar a ferramenta do CI

- [x] 1.1 Trocar somente `@latest` por `@1.14.0` na chamada OpenSpec do job de CI, preservando `validate --strict --all`.
- [x] 1.2 Confirmar que o workflow instala a versão exata fixada e não altera outros jobs, secrets ou passos de deploy. Evidência: `npx -y @fission-ai/openspec@1.14.0 --version` retornou `1.14.0`; diff restrito às duas chamadas do job `openspec`.

## 2. Validar a execução estrita

- [x] 2.1 Executar `openspec validate --strict --all` com OpenSpec 1.14.0 e confirmar os itens aprovados no checkout integrado. Evidência: `npx -y @fission-ai/openspec@1.14.0 validate --strict --all` retornou 78 aprovados, 0 falhas; o total inclui esta change.
- [x] 2.2 Revisar o diff focado, validar o OpenSpec da change e registrar evidência de que nenhuma validação foi suprimida. Evidência: `validate pin-openspec-cli-in-ci --type change --strict --no-interactive --json` retornou 1 aprovado, 0 falhas; `validate --strict --all` permaneceu integral e estrito.
