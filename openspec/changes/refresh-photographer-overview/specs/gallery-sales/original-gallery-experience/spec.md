## ADDED Requirements

### Requirement: Lista responsiva das galerias da cliente

A biblioteca autenticada SHALL apresentar uma entrada por jornada retornada, com capa disponível, estado de acesso, prazos por pasta e ações existentes. Os filtros locais SHALL usar os estados retornados no mesmo escopo de consulta.

#### Scenario: Cliente filtra suas galerias

- **WHEN** a cliente escolhe o filtro de galerias ativas ou expiradas
- **THEN** a interface mostra somente as jornadas daquele estado, ou informa que o filtro não encontrou resultados
- **AND** voltar ao filtro de todas as galerias apresenta a lista na ordem recebida

#### Scenario: Cliente encontra consulta indisponível

- **WHEN** a consulta da biblioteca falha
- **THEN** a tela informa a falha e oferece nova tentativa, sem apresentar galerias desatualizadas

### Requirement: Apresentação responsiva da coleção autenticada

A Galeria da cliente SHALL organizar o cabeçalho, os prazos, a coleção e o resumo de seleção conforme os dados da jornada autorizada. A coleção SHALL reutilizar a experiência de prévias protegidas e as operações existentes, incluindo a solicitação de reabertura quando autorizada.

#### Scenario: Cliente abre uma galeria

- **WHEN** o backend autoriza a consulta da galeria
- **THEN** a tela apresenta seu título e as pastas comuns e atribuídas disponíveis na coleção
- **AND** cada foto mantém os estados, proteções e ações já autorizados

#### Scenario: Dados de fotos ficam indisponíveis

- **WHEN** a consulta das fotos falha depois da autorização da galeria
- **THEN** a tela mantém o cabeçalho da galeria e oferece nova tentativa para atualizar a coleção

### Requirement: Histórico responsivo de compras e entregas

Minhas compras SHALL organizar os registros autorizados em cartões responsivos e preservar os agrupamentos, estados e links existentes de cada pedido.

#### Scenario: Cliente consulta a entrega

- **WHEN** um pedido autorizado aparece no histórico
- **THEN** seus itens e estado financeiro permanecem no mesmo registro
- **AND** a entrega usa somente o destino disponível e validado para o pedido

### Requirement: Ampliação de fotografia com navegação acessível

A ampliação SHALL mostrar a posição na sequência de fotos autorizadas e preservar as proteções da prévia e suas ações existentes. O foco SHALL ficar no diálogo aberto e voltar ao controle de abertura quando o diálogo fechar.

#### Scenario: Cliente navega entre fotos ampliadas

- **WHEN** a cliente amplia uma prévia e avança ou retorna
- **THEN** o visualizador atualiza a mídia protegida e a posição na sequência
- **AND** fechar retorna à coleção com foco no botão de origem

### Requirement: Revisão responsiva do carrinho e dos meios disponíveis

O carrinho SHALL apresentar fotos separadas por galeria, o resumo e os meios de pagamento habilitados com os dados retornados. Os grupos sem cobrança SHALL manter a finalização própria.

#### Scenario: Cliente revisa uma seleção com cobrança

- **WHEN** a cliente abre o carrinho
- **THEN** a interface organiza itens, estado das prévias e totais e oferece apenas os meios e ações disponíveis

#### Scenario: Cliente comunica um PIX

- **WHEN** a comunicação é aceita pelo servidor
- **THEN** a interface informa que o pagamento aguarda conferência e oferece acesso ao registro no histórico
