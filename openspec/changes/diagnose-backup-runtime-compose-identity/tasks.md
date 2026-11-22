# Tasks

## 1. Diagnóstico agregado

- [x] 1.1 Obter revisão e aceite do proprietário para os artefatos desta change antes de alterar código, conforme `INSTRUCOES_EXECUTOR_CLAUDE_CODE.md`; evidência: após receber a proposta e os quatro artefatos, o proprietário respondeu “prossiga” em 22/11/2026.
- [x] 1.2 Implementar a comparação read-only entre IDs da listagem de labels e IDs enumerados pelo Compose fixo; validar IDs completos, unicidade, limite de 512, consistência das duas leituras e resposta atômica. Evidência: `python -B scripts/test_platform_backup_runtime_inventory.py` passou (19 testes, 1 skip POSIX/root esperado) e Ruff passou nos dois arquivos alterados.

## 2. Integração protegida

- [x] 2.1 Atualizar schema do diagnóstico, operação allowlisted do wrapper e parser do workflow para publicar somente os agregados novos; evidência: `python -B scripts/test_platform_backup_runtime_workflow.py` validou respostas schema 2, erros allowlisted, recusa de campos extras e o validador pós-instalação.
- [x] 2.2 Atualizar hashes e guardas relacionadas somente aos caminhos autorizados; evidência: pin Git do módulo atualizado e conferido, allowlists existentes preservadas e verificadas por 30 testes de escopo; política de workflow, Ruff, Git Bash `-n`, `git diff --check` e `openspec validate --strict` passaram. Não foi necessária ampliação das allowlists.

## 3. Validação operacional read-only

- [ ] 3.1 Após change revisada, CI verde no SHA exato e preflight protegido atual, apresentar o inventário e o plano de impacto antes de qualquer operação no host; executar somente a consulta allowlisted do diagnóstico após autorização aplicável e registrar contagens sanitizadas.
- [ ] 3.2 Confirmar que o inventário normal ainda falha fechado enquanto a identidade continuar ambígua e que containers, serviço, timer e destino não foram alterados; não executar seleção, remoção, vínculo, ensaio, backup, restauração ou `operate`.
