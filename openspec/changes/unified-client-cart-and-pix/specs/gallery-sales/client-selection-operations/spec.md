## MODIFIED Requirements

### Requirement: Ficha individual de seleção e compra

O sistema SHALL fornecer ao fotógrafo uma ficha individual por galeria privada derivada com cliente proprietária, origem, prazo, estado de seleção, estado de pagamento, quantidade, totais e datas operacionais. Quando um pedido integrar um pagamento agrupado, a ficha SHALL distinguir o subtotal daquele pedido do valor total do pagamento e oferecer acesso ao conjunto. A operação das fotos e entregas SHALL permanecer individual por pedido, enquanto decisões financeiras do pagamento SHALL abranger todos os pedidos vinculados.

#### Scenario: Fotógrafo abre uma seleção
- **WHEN** o fotógrafo seleciona uma cliente na ficha de uma galeria-fonte
- **THEN** o sistema apresenta somente o resumo e a seleção daquela cliente, sem combinar dados de outras clientes

#### Scenario: Pedido integra pagamento único
- **WHEN** o fotógrafo consulta um pedido de R$ 35,00 vinculado a um pagamento de R$ 42,00
- **THEN** a ficha distingue os dois valores e permite consultar o outro pedido incluído, da mesma cliente
- **AND** os atalhos financeiros deixam claro que decidirão sobre R$ 42,00 e todos os pedidos do pagamento

## ADDED Requirements

### Requirement: Identificadores e produção preservados no pagamento agrupado

O sistema SHALL preservar a origem por galeria, pasta e foto na conferência administrativa e nas exportações existentes dos pedidos vinculados. Vincular pedidos ao mesmo PIX SHALL NOT conceder acesso entre clientes, alterar entregas ou transferir fotos entre galerias.

#### Scenario: Separação das fotos de uma galeria
- **WHEN** o fotógrafo exporta identificadores de um pedido integrante de uma compra com duas galerias
- **THEN** recebe somente os identificadores daquele pedido conforme o escopo solicitado
- **AND** a associação financeira com o outro pedido permanece consultável e auditável
