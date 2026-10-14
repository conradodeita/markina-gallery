# Validação

## Implementação local

- Teste de política do inventário: 7 testes aprovados. Inclui origem válida, ausente e inválida sem ecoar o valor; divergência entre origem esperada e Compose aborta antes das consultas de serviços e banco; preserva guards de SHA e escopo somente leitura.
- Sintaxe Bash do script remoto e dos blocos de execução do workflow: aprovada com Git Bash para Windows.
- Compilação sintática Python dos scripts de validação e teste: aprovada.
- Validação OpenSpec strict: aprovada, 1 change válido e nenhum issue.
- Verificação de whitespace do diff: aprovada.

## Verificação remota após integração

Pendente: requer revisão e integração desta correção em main, seguida da execução manual do workflow read-only com o SHA integral atualmente implantado. Essa execução deve usar o Environment protegido homolog e sua aprovação humana própria. Não houve conexão SSH, probe público ou alteração no servidor durante a validação local.

## CI do PR #184

- Política do inventário, OpenSpec, gitleaks e frontend: aprovados.
- Backend: falhou antes do checkout/testes durante a inicialização do serviço PostgreSQL; o runner recebeu “toomanyrequests: Data limit exceeded” ao baixar postgres:17-alpine do ECR. Não há evidência de falha causada pelo diff.
- Runtime Gemma: ainda em execução na última consulta. O resultado final deverá ser conferido antes da integração.
