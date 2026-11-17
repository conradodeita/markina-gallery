# Design

## Decisão

Usar o mecanismo `.gitleaksignore` já presente no repositório e adicionar a impressão digital completa retornada pelo Gitleaks. A linha terá comentário explicando a validação do placeholder. Como a exceção inclui commit, caminho, regra e linha, ela não desativa a regra `generic-api-key` em outros conteúdos.

## Segurança e validação

A análise confirmou que o valor detectado é exatamente o texto `REDACTED` (oito caracteres), em `openspec/changes/reopen-card-purchase-cart/validation.md`, no commit `2abb7d259e5b129c6a190320e6a4165bf5da87d3`, fora da ancestralidade do branch `feature/saas-release-candidate`. O conteúdo bruto do achado não será copiado para novos relatórios. A validação usará o Gitleaks 8.24.3 e as mesmas opções de varredura histórica definidas pela CI; nenhuma credencial será alterada.

## Alternativas consideradas

- Desativar `generic-api-key`: rejeitada, pois deixaria de detectar credenciais reais.
- Ignorar o arquivo inteiro: rejeitada, pois ocultaria achados futuros no recibo.
- Reescrever o histórico: rejeitada, pois é desnecessário para um placeholder e implicaria alteração de histórico compartilhado.
