# Spec Delta

## ADDED Requirements

### Requirement: Nome renomeado preserva o público da pasta

O sistema SHALL devolver o nome atual de uma pasta restrita somente às clientes com atribuição ativa, sem ampliar ou alterar o público durante uma renomeação administrativa.

#### Scenario: Cliente autorizada consulta pasta renomeada

- **WHEN** uma cliente com atribuição ativa consulta uma pasta restrita renomeada
- **THEN** a consulta apresenta o nome novo e mantém as mesmas fotos autorizadas

#### Scenario: Cliente sem atribuição consulta a galeria

- **WHEN** uma cliente sem atribuição consulta a galeria após a pasta restrita ser renomeada
- **THEN** a resposta continua omitindo a pasta e seu nome
