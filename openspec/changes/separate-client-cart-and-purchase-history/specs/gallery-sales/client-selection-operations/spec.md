## ADDED Requirements

### Requirement: Agregação visual sem combinação financeira

O sistema SHALL permitir que a cliente consulte em uma única superfície todos os seus carrinhos ainda não comunicados, agrupados por Galeria pública. Cada grupo SHALL conservar fotos, quantidade, subtotal, prazo, cotação, checkout e comunicação de pagamento próprios; o total entre galerias SHALL ser apenas informativo e SHALL NOT criar pedido, PIX ou pagamento combinado.

#### Scenario: Carrinhos de galerias diferentes

- **WHEN** a cliente possui seleções vigentes em duas ou mais Galerias públicas
- **THEN** o carrinho global apresenta um grupo identificável para cada galeria, com sua própria quantidade, subtotal e ação de revisão
- **AND** nenhuma ação permite finalizar as galerias como um único pedido

#### Scenario: Total geral do carrinho

- **WHEN** todos os carrinhos agrupados possuem cotação válida
- **THEN** a interface pode apresentar a soma de fotos e valores como resumo informativo
- **AND** identifica que a finalização ocorre separadamente por galeria

#### Scenario: Uma galeria possui erro de cotação

- **WHEN** uma das galerias não possui cotação válida
- **THEN** o erro e o bloqueio ficam contidos naquele grupo
- **AND** os demais carrinhos continuam identificáveis e utilizáveis de forma independente

### Requirement: Fronteira entre carrinho e compra

O sistema SHALL classificar como carrinho toda seleção ou conferência editável cujo pagamento ainda não foi comunicado. Ao registrar a comunicação do pagamento, o sistema SHALL remover imediatamente aquele pedido do carrinho e SHALL incluí-lo no histórico de compras da cliente, sem aguardar a confirmação administrativa.

#### Scenario: Checkout preparado sem comunicação

- **WHEN** a cliente chega ao QR Code mas ainda não aciona `Informar pagamento`
- **THEN** as fotos permanecem no carrinho editável da respectiva galeria
- **AND** não aparecem no histórico de compras

#### Scenario: Pagamento comunicado

- **WHEN** a cliente aciona `Informar pagamento` e o backend registra a comunicação
- **THEN** o pedido congelado sai do carrinho e aparece em `Compras` com estado `Pagamento informado`

#### Scenario: Pagamento confirmado

- **WHEN** o fotógrafo confirma o pagamento comunicado
- **THEN** o mesmo pedido permanece em `Compras` e passa ao estado `Pagamento confirmado` ou `Comprada`

#### Scenario: Compra complementar

- **WHEN** a cliente inicia uma nova seleção depois de comunicar um pagamento na mesma galeria
- **THEN** a nova seleção aparece como outro carrinho editável sem modificar a compra já registrada
