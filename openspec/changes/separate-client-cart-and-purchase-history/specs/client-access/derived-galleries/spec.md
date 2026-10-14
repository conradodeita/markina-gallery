## ADDED Requirements

### Requirement: Resumo global de carrinhos por jornada

A biblioteca autenticada SHALL resumir os carrinhos da cliente em todas as jornadas autorizadas sem expor dados de outra identidade e sem transformar a agregação visual em uma autoridade financeira compartilhada. Cada grupo SHALL apontar para a revisão da galeria privada correspondente.

#### Scenario: Cliente retorna com várias seleções

- **WHEN** a cliente autentica e possui seleções em galerias diferentes
- **THEN** a biblioteca restaura todos os grupos de carrinho e os identifica pela respectiva galeria ou evento
- **AND** cada ação abre somente a revisão autorizada daquele grupo

#### Scenario: Carrinho fica vazio após comunicação

- **WHEN** a última seleção de uma galeria é congelada por comunicação de pagamento
- **THEN** o grupo correspondente deixa de aparecer no carrinho global
- **AND** a jornada e a compra continuam acessíveis nos seus destinos próprios

### Requirement: Histórico financeiro separado das jornadas editáveis

A biblioteca autenticada SHALL obter e apresentar como histórico somente os pedidos da cliente cujo pagamento foi comunicado ou confirmado. O carregamento ou a falha desse histórico SHALL permanecer separado do carregamento dos carrinhos e das galerias autorizadas.

#### Scenario: Histórico demora ou falha

- **WHEN** a consulta de compras demora ou falha
- **THEN** os carrinhos e acessos às galerias continuam disponíveis
- **AND** somente a seção `Compras` apresenta carregamento, erro ou nova tentativa

#### Scenario: Pedido sem comunicação existe no servidor

- **WHEN** existe um rascunho ou checkout preparado sem comunicação de pagamento
- **THEN** a projeção de compras não o apresenta como histórico
- **AND** a projeção de carrinho continua oferecendo sua retomada na galeria correspondente
