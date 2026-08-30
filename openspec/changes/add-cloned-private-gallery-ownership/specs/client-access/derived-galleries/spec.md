## MODIFIED Requirements

### Requirement: Persistência do histórico privado

O sistema SHALL manter uma biblioteca visual para a cliente proprietária, onde ela retoma apenas suas galerias privadas derivadas, seleções, pedidos e histórico sem acesso ao acervo-mãe nem a galerias de terceiros. Fotos confirmadas em pedidos dessa cliente SHALL permanecer identificadas como já compradas no seu contexto privado.

#### Scenario: Biblioteca vazia

- **WHEN** a cliente autenticada não possui galeria derivada ativa nem entrega histórica
- **THEN** a interface mostra estado vazio claro sem sugerir ou revelar galerias de terceiros

#### Scenario: Histórico após expiração

- **WHEN** o prazo de seleção de uma galeria privada expira
- **THEN** a cliente continua acessando seus pedidos, entregas e identificação de fotos já compradas, sem poder criar seleção fora das regras de reativação

### Requirement: Interface da cliente orientada pelo backend

O sistema SHALL renderizar biblioteca, propriedade, permissões, prazo, interações, estados das fotos e histórico da cliente a partir de respostas autorizadas do backend. O frontend SHALL NOT inferir vínculo por link, telefone informado ou estado local.

#### Scenario: Permissão alterada

- **WHEN** o fotógrafo altera acesso, prazo ou permissões de uma galeria derivada
- **THEN** a cliente vê o novo estado retornado pelo backend sem o frontend conceder ou preservar permissão localmente

#### Scenario: Galeria de outra responsável

- **WHEN** uma cliente possui o URL ou identificador de uma galeria pertencente a outra responsável
- **THEN** a interface recebe somente resposta de acesso negado e não exibe metadados, fotos, favoritos, comentários ou pedidos dessa galeria
