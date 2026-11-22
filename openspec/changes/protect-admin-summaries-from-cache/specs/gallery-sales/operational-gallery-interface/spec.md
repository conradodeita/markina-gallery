# Spec Delta

## ADDED Requirements

### Requirement: Resumo de atividade administrativa não armazenável em cache

A resposta do resumo operacional autenticado SHALL incluir `Cache-Control: private, no-store` quando contiver atividade ou identidade de clientes.

#### Scenario: Fotógrafo consulta atividade recente
- **WHEN** uma sessão administrativa autenticada consulta o resumo operacional com seleções recentes
- **THEN** a resposta JSON mantém os campos existentes e instrui navegador e intermediários a não armazená-la em cache
