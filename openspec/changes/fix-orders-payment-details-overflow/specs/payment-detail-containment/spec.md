## ADDED Requirements

### Requirement: Contenção dos fatos do pagamento
O painel administrativo SHALL apresentar cada identificador e estado do pagamento em linha própria dentro do card, preservando o conteúdo integral e permitindo quebra de identificadores sem espaços, tanto em desktop como em mobile e nos temas claro e escuro.

#### Scenario: Identificadores Orders extensos
- **WHEN** um pedido Mercado Pago contém identificadores de order e transação sem espaços
- **THEN** cada rótulo e valor permanece dentro do painel sem sobrepor células vizinhas nem exigir truncamento do identificador

#### Scenario: Preservação dos demais detalhes
- **WHEN** o fotógrafo consulta metadados, fotografias e ações do pedido
- **THEN** os contratos financeiros e os demais layouts e ações permanecem preservados
