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
