## ADDED Requirements

### Requirement: Acesso permanente ao carrinho e aos pedidos

O portal da cliente SHALL apresentar acesso visível ao carrinho autoritativo e aos pedidos daquela identidade na jornada corrente. O atalho SHALL mostrar a quantidade do carrinho, e a conferência SHALL exibir somente miniaturas selecionadas, total, estado e próxima ação; fechar ou atualizar a página SHALL NOT tornar essas etapas invisíveis.

#### Scenario: Carrinho com fotos

- **WHEN** a cliente autenticada abre a Galeria pública, a privada contextual ou sua biblioteca com seleção vigente
- **THEN** ela vê `Carrinho (n)` e consegue retomar a conferência das fotos selecionadas

#### Scenario: Pedido com pagamento informado

- **WHEN** a cliente retorna depois de comunicar o pagamento
- **THEN** ela encontra o pedido congelado, suas fotos e o estado curto `Pagamento informado`

#### Scenario: Pedido confirmado

- **WHEN** o fotógrafo confirma o pagamento
- **THEN** as fotos do pedido aparecem para aquela cliente como `Compradas` e continuam acessíveis no histórico autorizado

### Requirement: Estado comercial visível por foto

O portal SHALL identificar de forma consistente cada foto da cliente como disponível, selecionada, com pagamento informado ou comprada, tanto na grade completa quanto na privada e nos resultados faciais da mesma galeria. O estado SHALL ser fornecido pelo backend e SHALL NOT ser inferido de armazenamento local do navegador.

#### Scenario: Resultado facial já selecionado

- **WHEN** uma foto encontrada pelo reconhecimento facial já pertence ao carrinho da cliente
- **THEN** o resultado mostra `Selecionada` e aponta para o mesmo carrinho, sem duplicar a seleção

#### Scenario: Foto de pedido congelado

- **WHEN** a foto pertence a pedido com pagamento comunicado ou confirmado
- **THEN** a grade mostra respectivamente `Pagamento informado` ou `Comprada` e não a oferece para recompra naquele mesmo pedido

### Requirement: Linguagem essencial na área da cliente

O portal SHALL usar textos curtos orientados a estado e ação, evitando explicar entidades internas, persistência técnica ou regras já evidentes na interface. Títulos, cards e estados vazios SHALL preservar acessibilidade e informação necessária sem repetir a mesma orientação em vários níveis.

#### Scenario: Cliente abre a biblioteca

- **WHEN** a biblioteca autorizada é carregada
- **THEN** ela usa o título `Minhas fotos`, estados comerciais curtos e ações como `Ver fotos`, `Carrinho` ou `Ver pedido`, sem exibir `Sua área privada`, `Cada evento aparece uma única vez` ou `compras preservadas`

#### Scenario: Biblioteca sem seleção nem pedido

- **WHEN** a cliente não possui fotos selecionadas nem pedidos
- **THEN** a interface apresenta um estado vazio curto e uma única próxima ação quando houver galeria disponível
