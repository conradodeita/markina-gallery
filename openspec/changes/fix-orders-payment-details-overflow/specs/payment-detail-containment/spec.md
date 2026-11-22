## ADDED Requirements

### Requirement: Contenção dos fatos do pagamento
O painel administrativo SHALL apresentar cada identificador e estado do pagamento em linha própria dentro do card, preservando o conteúdo integral e permitindo quebra de identificadores sem espaços, tanto em desktop como em mobile e nos temas claro e escuro.

#### Scenario: Identificadores Orders extensos
- **WHEN** um pedido Mercado Pago contém identificadores de order e transação sem espaços
- **THEN** cada rótulo e valor permanece dentro do painel sem sobrepor células vizinhas nem exigir truncamento do identificador

#### Scenario: Preservação dos demais detalhes
- **WHEN** o fotógrafo consulta metadados, fotografias e ações do pedido
- **THEN** os contratos financeiros e os demais layouts e ações permanecem preservados

### Requirement: Contenção dos filtros administrativos
O painel SHALL distribuir Mais filtros conforme a largura disponível, mantendo labels, selects, datas e botão dentro de suas células sem sobreposição. As opções e critérios financeiros SHALL permanecer inalterados.

#### Scenario: Situação financeira ao lado de Provedor
- **WHEN** o fotógrafo abre Mais filtros no desktop ou mobile
- **THEN** Situação financeira e Provedor não se sobrepõem e os controles permanecem utilizáveis dentro da grade
