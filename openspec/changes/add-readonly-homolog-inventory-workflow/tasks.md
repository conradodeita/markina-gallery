## 1. Change OpenSpec

- [x] 1.1 Registrar proposta, requisito de inventário somente leitura, decisões e critérios verificáveis aprovados.
- [x] 1.2 Validar a change com OpenSpec estrito e revisar coerência dos artefatos (`openspec validate add-readonly-homolog-inventory-workflow --strict`: válido).

## 2. Implementação

- [x] 2.1 Criar workflow manual isolado, disponível somente em `main`, com ambiente `homolog`, permissões mínimas, SHA obrigatório e SSH com host key estrita.
- [x] 2.2 Criar script remoto com paths/projeto fixos, comparação de SHA antes de consultas e coleta minimizada de métricas agregadas.
- [x] 2.3 Adicionar testes direcionados para SHA inválido/divergente, escopo Compose e ausência de operações mutáveis (`scripts/test_readonly_homolog_inventory_policy.py`: 3 aprovados).
- [x] 2.4 Executar validações Bash, testes direcionados e validação OpenSpec; evidências: Bash syntax válida, 3 testes de política aprovados, YAML parseável, `openspec validate --strict --all`: 2 passaram, 0 falharam.

## 3. Uso operacional posterior

- [ ] 3.1 Abrir PR somente para `main` e aguardar CI/revisão; mergear esta ferramenta não implanta a aplicação.
- [ ] 3.2 Após o merge, executar o inventário contra o SHA realmente implantado e registrar seu resultado minimizado antes de propor qualquer deploy.
