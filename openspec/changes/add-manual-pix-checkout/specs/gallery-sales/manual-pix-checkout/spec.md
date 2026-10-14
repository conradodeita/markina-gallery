## Purpose

Definir a seleção e compra privada de fotos com preço por faixa, checkout imutável e pagamento PIX manual, sem confirmação automática ou exposição de dados de outras clientes.

## ADDED Requirements

### Requirement: Seleção privada e carrinho persistente

O sistema SHALL manter uma seleção persistente por cliente autorizada e galeria derivada. A cliente SHALL poder incluir ou remover somente fotos liberadas de sua própria galeria, e o carrinho SHALL informar quantidade e estimativa comercial sem inferir autorização no navegador.

#### Scenario: Cliente altera seleção própria

- **WHEN** uma cliente autenticada inclui ou remove uma foto liberada de sua galeria derivada ativa
- **THEN** o sistema persiste a alteração somente para aquela cliente e atualiza o carrinho sem revelar fotos ou seleções de outra responsável

#### Scenario: Foto não elegível

- **WHEN** a cliente tenta selecionar foto não liberada, de outra galeria ou já confirmada em pedido próprio
- **THEN** o sistema recusa a ação sem revelar o estado comercial ou o conteúdo de terceiros

### Requirement: Preço por faixas controlado pelo fotógrafo

O sistema SHALL permitir ao fotógrafo configurar faixas contíguas de quantidade e preço unitário em centavos inteiros para uma galeria derivada ou sua origem permitida. O carrinho SHALL calcular o total aplicando uma única faixa à quantidade inteira e SHALL informar quando a próxima faixa altera a estimativa.

#### Scenario: Cliente atinge uma faixa

- **WHEN** a quantidade de fotos selecionadas corresponde a uma faixa ativa
- **THEN** o sistema mostra preço unitário e total calculados em centavos inteiros pela faixa correspondente

#### Scenario: Fotógrafo configura salto comercial

- **WHEN** uma alteração de faixa faria o total diminuir ao aumentar a quantidade mínima
- **THEN** o painel do fotógrafo alerta o efeito antes de salvar a regra

### Requirement: Checkout comercial imutável

O sistema SHALL permitir que a cliente autenticada finalize fotos selecionadas elegíveis em um novo pedido. O pedido SHALL congelar fotos, nomes, regra de preço, preços unitários, total e texto comercial aplicados no momento do checkout, sem alterar pedidos anteriores.

#### Scenario: Checkout válido

- **WHEN** a cliente finaliza uma seleção não vazia durante o prazo ativo da galeria
- **THEN** o sistema cria um pedido pendente com os snapshots comerciais e remove do carrinho somente as fotos incluídas nele

#### Scenario: Novo pedido após confirmação

- **WHEN** a cliente já possui pedido confirmado e seleciona outras fotos elegíveis na mesma galeria ativa
- **THEN** o sistema cria um novo pedido sem modificar o pedido confirmado anterior

### Requirement: PIX manual pendente de confirmação

O sistema SHALL apresentar instruções controladas de PIX manual, incluindo QR Code ou copia-e-cola quando configurados, apenas para a cliente proprietária de um pedido pendente. A exibição ou ação da cliente SHALL NOT confirmar financeiramente o pedido.

#### Scenario: Cliente consulta pedido pendente próprio

- **WHEN** a cliente autenticada abre um pedido pendente de sua própria galeria derivada
- **THEN** ela vê o valor congelado e as instruções PIX disponíveis, com indicação de que a confirmação é manual pelo fotógrafo

#### Scenario: Tentativa de acesso a pedido de outra cliente

- **WHEN** uma cliente tenta consultar instruções PIX de pedido que não lhe pertence
- **THEN** o sistema nega a consulta sem revelar valor, chave, QR Code, copia-e-cola ou metadados do pedido
