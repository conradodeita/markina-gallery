## Purpose

Permitir que o fotógrafo confirme manualmente pagamentos comunicados pelo cliente, mantendo pedido, decisão e histórico coerentes e auditáveis.

## ADDED Requirements

### Requirement: Comunicação de pagamento pelo cliente

O sistema SHALL permitir que o cliente autorizado comunique pagamento para um pedido pendente pertencente à sua própria galeria derivada, sem alterar o pedido para confirmado automaticamente.

#### Scenario: Comunicação válida

- **WHEN** o cliente comunica pagamento de um pedido pendente próprio
- **THEN** o sistema registra a comunicação com data e estado pendente de revisão e informa que a confirmação depende do fotógrafo

#### Scenario: Pedido de outro cliente

- **WHEN** um cliente tenta comunicar pagamento de pedido que não lhe pertence
- **THEN** o sistema nega a operação sem revelar dados do pedido

### Requirement: Decisão manual e auditável

O sistema SHALL permitir ao fotógrafo confirmar ou recusar manualmente uma comunicação pendente, registrando a decisão, o responsável e a data em UTC.

#### Scenario: Confirmação pelo fotógrafo

- **WHEN** o fotógrafo confirma uma comunicação pendente
- **THEN** o pedido passa a pagamento confirmado uma única vez e a decisão fica disponível no histórico privado do cliente

#### Scenario: Recusa pelo fotógrafo

- **WHEN** o fotógrafo recusa uma comunicação pendente
- **THEN** o pedido permanece sem pagamento confirmado e o cliente recebe o estado correspondente sem exposição de dados internos

#### Scenario: Decisão repetida

- **WHEN** o fotógrafo ou uma requisição repetida tenta decidir uma comunicação já decidida
- **THEN** o sistema não altera a primeira decisão e registra ou devolve resultado idempotente sem duplicar efeitos
