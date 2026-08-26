## Purpose

Oferecer ao fotógrafo indicadores auditáveis de conversão de fotos selecionadas em compras confirmadas, sem misturar pedidos pendentes com receita efetiva.

## ADDED Requirements

### Requirement: Estatísticas de seleção e compra

O sistema SHALL disponibilizar ao fotógrafo uma página administrativa com contagens de fotos distintas compradas e de fotos selecionadas sem compra confirmada, filtráveis por período, evento, acervo-mãe e galeria derivada.

#### Scenario: Foto comprada

- **WHEN** uma foto integra ao menos um pedido com pagamento confirmado dentro dos filtros
- **THEN** a estatística a contabiliza como comprada segundo a regra de agregação exibida ao fotógrafo

#### Scenario: Foto selecionada não comprada

- **WHEN** uma foto está selecionada na galeria derivada mas não integra pedido com pagamento confirmado dentro dos filtros
- **THEN** a estatística a contabiliza como selecionada e não comprada

### Requirement: Listas e exportação de fotos

O sistema SHALL exibir as listas de fotos compradas e selecionadas não compradas, e permitir ao fotógrafo baixar a lista não comprada em arquivo TXT UTF-8 contendo somente identificador e nome de arquivo da foto.

#### Scenario: Exportação filtrada

- **WHEN** o fotógrafo solicita o TXT após aplicar filtros de estatística
- **THEN** o sistema gera o arquivo correspondente à lista não comprada visível, sem incluir dados pessoais de clientes ou URLs de mídia

### Requirement: Receita confirmada ao longo do tempo

O sistema SHALL mostrar o valor em centavos de vendas com pagamento confirmado e um gráfico temporal compatível com o período filtrado.

#### Scenario: Pedido pendente

- **WHEN** um pedido ainda não possui pagamento confirmado
- **THEN** seu valor não integra a receita confirmada nem os pontos do gráfico

#### Scenario: Período sem vendas

- **WHEN** o filtro não possui pagamentos confirmados
- **THEN** o sistema apresenta receita zero e estado vazio claro para o gráfico
