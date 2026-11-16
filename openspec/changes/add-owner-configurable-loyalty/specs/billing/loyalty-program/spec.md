# billing/loyalty-program Specification

## ADDED Requirements

### Requirement: Configuração global sem política presumida

O proprietário global SHALL configurar eventos elegíveis, critérios, quantidades de pontos, conversões ou recompensas, benefícios e estado ativo/inativo. O sistema MUST iniciar sem regra comercial ativa ou valor presumido. Somente uma permissão comercial global explícita SHALL autorizar alterações.

#### Scenario: Instalação sem regra

- **WHEN** ainda não há política aprovada e configurada
- **THEN** nenhuma pontuação ou recompensa é concedida automaticamente

### Requirement: Ledger de pontos próprio e idempotente

O sistema SHALL manter saldo e histórico de pontos em ledger próprio, distinto da carteira de créditos e dos pagamentos. A mesma regra não pode pontuar duas vezes o mesmo evento; retry e processamento concorrente MUST permanecer idempotentes. Suspender uma regra SHALL conservar os movimentos já registrados.

#### Scenario: Evento repetido

- **WHEN** o mesmo evento é reprocessado ou entregue mais de uma vez
- **THEN** a regra concede pontos no máximo uma vez e mantém uma referência auditável à origem

### Requirement: Recompensa vinculada ao evento de origem

Cada recompensa automática SHALL referenciar o evento e a regra que a produziram. Quando a recompensa conceder créditos, ela SHALL criar movimento próprio no ledger de créditos, relacionado à recompensa sem misturar a contabilidade. Créditos concedidos como recompensa MUST NOT expirar.

#### Scenario: Recompensa em créditos

- **WHEN** uma regra aprovada concede créditos
- **THEN** o ledger de pontos registra origem/recompensa e o ledger de créditos registra o crédito correspondente com referência auditável

### Requirement: Consulta do fotógrafo

O fotógrafo autenticado SHALL consultar somente seus pontos, saldo, histórico e recompensas do próprio tenant. Nenhum tenant pode consultar ou alterar registros de fidelidade de outro.

#### Scenario: Acesso cruzado

- **WHEN** a sessão tenta abrir saldo ou movimento de outro tenant
- **THEN** a API recusa sem revelar dados ou regras internas de outra conta
