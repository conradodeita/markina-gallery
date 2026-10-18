# Spec Delta

## Purpose

Permitir que cada fotógrafo tenha um hostname HTTPS próprio para Compras, resolvendo o tenant por registro canônico e preservando o isolamento comercial já definido pelo piloto multitenant.

## ADDED Requirements

### Requirement: Subdomínio canônico seleciona contexto de Compras

O sistema SHALL resolver o tenant a partir do hostname HTTPS canônico previamente associado ao fotógrafo. O hostname seleciona o contexto da requisição, mas SHALL NOT conceder acesso ao pedido ou substituir a identidade e propriedade verificadas no backend.

#### Scenario: Subdomínio ativo
- **WHEN** uma cliente autenticada abre Compras pelo hostname canônico de um fotógrafo
- **THEN** o backend consulta somente pedidos da sessão cliente e do tenant resolvido para esse hostname

#### Scenario: Mesmo telefone em outro fotógrafo
- **WHEN** uma pessoa com mesmo telefone possui cadastro independente em A e B e usa sessão de B no subdomínio A
- **THEN** a sessão de B não autoriza consulta de Compras de A nem expõe pedidos ou dados de B

#### Scenario: Hostname desconhecido ou adulterado
- **WHEN** a requisição chega por host não registrado, inativo ou por cabeçalho encaminhado não confiável
- **THEN** o sistema falha fechado, sem fallback para outro tenant ou entrega de dados comerciais

### Requirement: Origem do link de pedido usa hostname canônico

O sistema SHALL gerar o link interno de Compras com o hostname canônico do tenant persistido no pedido. Falta ou ambiguidade na associação SHALL impedir a geração do link e não SHALL selecionar outro fotógrafo.

#### Scenario: Pedido com tenant inequívoco
- **WHEN** um aviso é gerado para pedido associado a um tenant ativo com hostname canônico
- **THEN** o destino usa esse hostname e a âncora do pedido correspondente

#### Scenario: Pedido sem tenant inequívoco
- **WHEN** não é possível resolver exatamente um tenant ativo e seu hostname para o pedido
- **THEN** nenhuma URL é gerada para outro fotógrafo e o aviso falha de modo sanitizado
