# Spec Delta

## ADDED Requirements

### Requirement: Identificar clientes das pastas privadas na etapa Imagens
A etapa Imagens SHALL apresentar as pastas pertencentes às galerias privadas derivadas em uma seção separada das pastas públicas e identificar a cliente principal e todos os membros ativos de cada galeria privada. Os dados SHALL vir de consulta administrativa autorizada do backend.

#### Scenario: Galeria privada com uma cliente
- **WHEN** o fotógrafo consulta a etapa Imagens de uma galeria-fonte que possui galerias privadas com pastas
- **THEN** a seção privada identifica cada galeria pela cliente principal e lista suas pastas sem misturá-las ao upload público

#### Scenario: Galeria privada compartilhada
- **WHEN** uma galeria privada possui mais de um membro ativo
- **THEN** a seção identifica a cliente principal e apresenta os nomes dos demais membros ativos associados

#### Scenario: Sem pastas privadas
- **WHEN** nenhuma galeria privada derivada da galeria-fonte possui pastas
- **THEN** a etapa Imagens apresenta um estado vazio específico para a seção privada e mantém as pastas públicas independentes

#### Scenario: Escopo e autorização
- **WHEN** um administrador consulta ou outra sessão tenta consultar a seção privada
- **THEN** o backend retorna somente galerias, pastas e membros vinculados à galeria-fonte autorizada dentro do tenant da sessão, responde como não encontrada para origem de outro tenant e não disponibiliza dados privados a clientes
