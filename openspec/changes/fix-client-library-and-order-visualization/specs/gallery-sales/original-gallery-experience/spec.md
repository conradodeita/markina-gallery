## ADDED Requirements

### Requirement: Estados comerciais coerentes na galeria privada

A galeria privada da cliente SHALL agrupar e contar fotos pelos estados comerciais fornecidos pelo backend: selecionada no carrinho, aguardando pagamento, pagamento informado e comprada. A interface SHALL NOT apresentar como contagem principal categorias de navegação que excluam fotos comerciais válidas, e SHALL manter `Todas` como o total autorizado da grade.

#### Scenario: Pedidos pendentes presentes

- **WHEN** a grade contém fotos em pedidos aguardando pagamento ou com pagamento informado
- **THEN** os respectivos filtros mostram contagens não nulas e exibem exatamente essas fotos ao serem selecionados

#### Scenario: Carrinho e compra confirmada coexistem

- **WHEN** a cliente possui fotos selecionadas e fotos já compradas na mesma galeria
- **THEN** `Carrinho` e `Compradas` apresentam contagens independentes sem duplicar nem omitir fotos em `Todas`

#### Scenario: Estado ausente

- **WHEN** não há fotos em determinado estado comercial
- **THEN** o filtro apresenta zero de forma coerente e não altera a contagem total autorizada

### Requirement: Galeria privada sem capa editorial vazia

A superfície privada usada pela cliente para revisar fotos e acompanhar pedidos SHALL priorizar grade, filtros, carrinho e histórico comercial, e SHALL NOT renderizar espaço de capa ou a mensagem `Capa ainda não definida`. A Galeria pública e as superfícies administrativas SHALL preservar sua apresentação de capa conforme a configuração vigente.

#### Scenario: Cliente abre a galeria privada

- **WHEN** a cliente abre sua galeria privada autorizada
- **THEN** a primeira composição útil apresenta controles e fotos sem reservar área para uma capa editorial ausente

#### Scenario: Galeria pública com capa

- **WHEN** a cliente abre a Galeria pública correspondente
- **THEN** a capa configurada continua sendo apresentada normalmente

### Requirement: Acompanhamento de pedidos distinguível

O acompanhamento do pagamento SHALL separar visualmente cada pedido, mantendo seu identificador, fotos, valor, estado e próxima ação no mesmo agrupamento. Pedidos aguardando pagamento, com pagamento informado, confirmados ou cancelados SHALL ter espaçamento e tratamento visual distintos sem alterar o estado financeiro retornado pelo backend.

#### Scenario: Vários pedidos na mesma galeria

- **WHEN** a cliente possui dois ou mais pedidos na mesma galeria
- **THEN** cada pedido aparece em um bloco separado com espaço suficiente para reconhecer seus limites e suas próprias fotos

#### Scenario: Estados de pagamento diferentes

- **WHEN** pedidos aguardando pagamento, informados e confirmados aparecem juntos
- **THEN** cor, rótulo e hierarquia permitem diferenciar os estados sem depender apenas da cor
