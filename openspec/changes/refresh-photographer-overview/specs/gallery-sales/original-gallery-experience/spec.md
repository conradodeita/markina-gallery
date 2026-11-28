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
