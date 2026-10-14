# gallery-sales/client-selection-operations Specification

## Purpose
Definir a operação administrativa da seleção individual de uma cliente, com conferência visual protegida, status comercial e exportação portátil dos identificadores de fotos.

## Requirements

### Requirement: Ficha individual de seleção e compra
O sistema SHALL fornecer ao fotógrafo uma ficha individual por galeria privada derivada com cliente proprietária, origem, prazo, estado de seleção, estado de pagamento, quantidade, totais e datas operacionais.

#### Scenario: Fotógrafo abre uma seleção
- **WHEN** o fotógrafo seleciona uma cliente na ficha de uma galeria-fonte
- **THEN** o sistema apresenta somente o resumo e a seleção daquela cliente, sem combinar dados de outras clientes

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
O sistema SHALL manter congeladas as fotos, valores e regras de um pedido confirmado. A cliente poderá realizar um novo pedido distinto de fotos ainda elegíveis enquanto sua galeria estiver ativa.

#### Scenario: Cliente compra fotos adicionais
- **WHEN** uma cliente com pedido confirmado seleciona novas fotos em galeria ainda ativa
- **THEN** o sistema cria um novo fluxo de pedido sem alterar o pedido já confirmado

### Requirement: Download das fotos compradas em Vendas e pagamentos
O sistema SHALL oferecer “Baixar fotos compradas” junto às ações financeiras do card de pedido confirmado em “Vendas e pagamentos”. A ação SHALL reutilizar a exportação HTML administrativa e incluir somente compras confirmadas da mesma cliente naquela galeria.

#### Scenario: Baixar fotos após confirmar pagamento
- **WHEN** o fotógrafo confirma o pagamento de um pedido na tela “Vendas e pagamentos”
- **THEN** o card oferece “Baixar fotos compradas” junto às ações financeiras e o navegador baixa o HTML das compras confirmadas da cliente naquela galeria

#### Scenario: Cliente possui compras confirmadas em mais de um pedido
- **WHEN** a cliente possui mais de um pedido confirmado na mesma galeria
- **THEN** o relatório iniciado por qualquer card confirmado daquela cliente inclui os itens de todos esses pedidos confirmados, sem incluir pedidos pendentes, recusados ou não localizados

#### Scenario: Pedido não confirmado
- **WHEN** o pedido está aguardando, informado, recusado, não localizado ou teve a confirmação corrigida
- **THEN** o card não oferece a ação de download para esse pedido e a autorização do endpoint continua recusando uma exportação sem compra confirmada

### Requirement: Nome seguro para o HTML de compras
O arquivo SHALL ser HTML autônomo, manter a extensão `.html` e usar um nome que contenha o nome da cliente. O nome SHALL remover controles, separadores de caminho e caracteres incompatíveis com nomes de arquivo, preservando caracteres Unicode quando suportados.

#### Scenario: Nome do cliente contém caracteres especiais
- **WHEN** o nome da cliente contém acentos, aspas, controles ou caracteres que não podem compor um nome de arquivo
- **THEN** o nome baixado preserva a forma legível quando suportada pelo navegador, remove caracteres inseguros e mantém a extensão `.html`, sem alterar o nome exibido dentro do relatório
