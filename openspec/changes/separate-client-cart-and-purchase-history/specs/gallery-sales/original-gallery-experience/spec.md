## ADDED Requirements

### Requirement: Navegação comercial separada por intenção

O portal da cliente SHALL apresentar `Carrinho` como acesso àquilo que ainda pode ser revisado e pago e `Compras` como acesso ao histórico cujo pagamento já foi comunicado. Rótulos e destinos SHALL NOT usar `Ver pedido` para encaminhar a cliente a uma superfície que mistura seleção, filtros, carrinho e histórico.

#### Scenario: Cliente possui somente seleção

- **WHEN** a cliente possui fotos selecionadas e nenhum pagamento comunicado
- **THEN** a ação comercial principal é `Carrinho`
- **AND** nenhuma ação sugere que essa seleção já integra o histórico de compras

#### Scenario: Cliente possui somente compra comunicada

- **WHEN** a cliente não possui seleção editável e possui pedido com pagamento comunicado
- **THEN** a ação comercial principal é `Compras` ou `Ver compra`
- **AND** seu destino apresenta o histórico financeiro correspondente

#### Scenario: Carrinho e compras coexistem

- **WHEN** a cliente possui uma nova seleção e compras anteriores
- **THEN** os dois acessos aparecem separados, com quantidades e estados coerentes

### Requirement: Histórico de compras essencial e sem filtros

A superfície `Compras` SHALL exibir somente pedidos com pagamento comunicado ou confirmado e SHALL limitar seu conteúdo a galeria, fotos, quantidade, valor, data, estado e ação de ampliação necessária. Essa superfície SHALL NOT apresentar filtros de fotos, controles de seleção, fotos disponíveis nem pedidos cujo pagamento não foi comunicado.

#### Scenario: Cliente abre Compras

- **WHEN** a cliente acessa `Compras` ou `Ver compra`
- **THEN** vê somente cards de compras comunicadas ou confirmadas, separados por pedido e galeria
- **AND** não vê filtros comerciais ou de navegação

#### Scenario: Compra possui várias fotos

- **WHEN** a cliente expande uma compra
- **THEN** as fotos daquele pedido aparecem juntas em grade responsiva e podem ser ampliadas
- **AND** não podem ser selecionadas, desmarcadas ou misturadas com outro pedido

#### Scenario: Nenhuma compra comunicada

- **WHEN** a cliente ainda não comunicou pagamento em pedido algum
- **THEN** `Compras` apresenta um estado vazio curto sem listar o conteúdo do carrinho
