# Tasks

## 1. Cabeçalhos e contratos

- [x] 1.1 Adicionar `Cache-Control: private, no-store` às rotas administrativas de resumo de segurança e atividade, sem alterar autenticação ou payload; validar com testes backend que ambos os cabeçalhos são retornados e os campos atuais permanecem presentes. Evidência: seis testes backend focados aprovados em `validation.md`.
- [x] 1.2 Revisar a área afetada conforme a política de refatoração contínua e rodar os testes backend focalizados, Ruff e `openspec validate --strict`; registrar evidência em `validation.md`. `git diff --check` passou; Gitleaks não encontrou segredos nos arquivos relacionados. Limitações e evidências completas em `validation.md`.
