# gallery-sales/client-selection-operations Specification

## Purpose
Definir a operação administrativa da seleção individual de uma cliente, com conferência visual protegida, status comercial e exportação portátil dos identificadores de fotos.

## Requirements

### Requirement: Ficha individual de seleção e compra

O sistema SHALL fornecer ao fotógrafo uma ficha individual por combinação de galeria e cliente, com vínculo, prazo, estado de seleção, pagamento, quantidade, totais e datas operacionais, sem exigir galeria derivada.

#### Scenario: Fotógrafo abre uma seleção

- **WHEN** o fotógrafo expande `Acervo da cliente` no card de uma cliente vinculada
- **THEN** vê somente resumo, fotos e pedidos daquela cliente, sem combinar dados das demais

### Requirement: Conferência administrativa das fotos escolhidas
O sistema SHALL permitir ao fotógrafo visualizar prévias sem marca d'água das fotos selecionadas, ampliar a prévia e consultar o nome ou identificador de cada arquivo. Essa prévia sem marca d'água SHALL ser exclusiva da área administrativa autorizada.

#### Scenario: Conferência de pedido
- **WHEN** o fotógrafo revisa as fotos de uma seleção ou pedido
- **THEN** ele vê miniaturas protegidas pelo controle administrativo, identificação de cada foto e ação de ampliação

### Requirement: Exportação de identificadores da seleção
O sistema SHALL permitir ao fotógrafo exportar a lista de identificadores das fotos selecionadas em formato TXT e CSV, sem expor URLs de originais nem dados de outros clientes.

#### Scenario: Separação no fluxo externo do fotógrafo
- **WHEN** o fotógrafo solicita exportação de uma seleção
- **THEN** o sistema gera um arquivo com os identificadores das fotos daquela seleção e registra a operação de exportação

### Requirement: Imutabilidade comercial após confirmação

O sistema SHALL manter congeladas as fotos, valores e regras de um pedido confirmado. A cliente poderá realizar novo pedido distinto de fotos ainda elegíveis enquanto seu prazo de seleção naquela galeria estiver ativo.

#### Scenario: Cliente compra fotos adicionais

- **WHEN** uma cliente com pedido confirmado seleciona novas fotos autorizadas na mesma galeria ainda ativa
- **THEN** o sistema cria novo fluxo de pedido sem alterar o pedido confirmado
