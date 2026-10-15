## ADDED Requirements

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

