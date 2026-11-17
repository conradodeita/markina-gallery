# Spec Delta

## ADDED Requirements

### Requirement: Resumo de segurança administrativa não armazenável em cache

A resposta do resumo de segurança da conta administrativa SHALL incluir `Cache-Control: private, no-store`.

#### Scenario: Fotógrafo consulta o resumo de segurança
- **WHEN** uma sessão administrativa autenticada consulta o próprio resumo de segurança
- **THEN** a resposta JSON mantém os campos existentes e instrui navegador e intermediários a não armazená-la em cache
