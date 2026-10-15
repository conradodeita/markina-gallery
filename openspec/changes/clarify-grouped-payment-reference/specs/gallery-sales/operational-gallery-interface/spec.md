# Spec Delta

## ADDED Requirements

### Requirement: Referência de compra agrupada no painel financeiro
O painel financeiro SHALL apresentar a compra agrupada pela referência curta já existente para o pagamento, igual à referência usada pelas mensagens e por “Compras”, e SHALL listar os pedidos individuais vinculados com seus códigos existentes e suas galerias. A apresentação SHALL preservar todos os identificadores persistidos e snapshots históricos.

#### Scenario: Localizar pagamento agrupado pela notificação
- **WHEN** o fotógrafo abre no painel um pagamento informado com código `bebb98d7` recebido na notificação
- **THEN** encontra a compra agrupada usando o mesmo código exibido em “Compras”
- **AND** vê os pedidos por galeria, incluindo o código individual existente de cada pedido

#### Scenario: Pedido legado sem agrupamento
- **WHEN** o fotógrafo consulta um pedido sem grupo de pagamento
- **THEN** o painel mantém a referência curta existente do pedido e suas ações operacionais
- **AND** não cria compra agrupada nem altera o código histórico

### Requirement: Alcance explícito das decisões financeiras agrupadas
O painel SHALL identificar as galerias e os pedidos abrangidos por uma decisão financeira agrupada e SHALL informar que confirmar, recusar ou corrigir a decisão afeta a compra agrupada inteira.

#### Scenario: Revisar o alcance antes da decisão
- **WHEN** o fotógrafo abre ações de uma compra agrupada com pedidos de várias galerias
- **THEN** vê o total do pagamento e todos os pedidos e galerias abrangidos antes de decidir
- **AND** a interface apresenta a ação como decisão da compra agrupada, sem sugerir que somente o pedido exibido será atualizado

#### Scenario: Pedido isolado
- **WHEN** o fotógrafo abre a decisão de um pedido sem agrupamento
- **THEN** a interface identifica o pedido individual e mantém o alcance atual da ação

### Requirement: Contexto coerente em mensagens de pagamento
Mensagens de pagamento SHALL descrever a referência conforme seu escopo: compra agrupada para pagamentos com grupo e pedido associado à galeria para pagamentos individuais. Uma mensagem agrupada SHALL NOT combinar a expressão “da galeria” com o valor “sua compra”.

#### Scenario: Confirmação de pagamento agrupado
- **WHEN** o fotógrafo confirma um PIX agrupado identificado por `bebb98d7`
- **THEN** a cliente recebe uma mensagem que identifica o pagamento como compra agrupada usando o mesmo código
- **AND** o texto não diz “da galeria sua compra”

#### Scenario: Confirmação de pedido individual
- **WHEN** o fotógrafo confirma um pagamento de pedido legado sem agrupamento
- **THEN** a cliente recebe o código existente do pedido e o nome da galeria correspondente

#### Scenario: Histórico de notificações
- **WHEN** novos templates contextuais são aplicados a pagamentos futuros
- **THEN** mensagens já enviadas e snapshots de notificações já persistidos permanecem inalterados
