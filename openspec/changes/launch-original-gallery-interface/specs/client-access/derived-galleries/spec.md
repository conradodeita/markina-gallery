## MODIFIED Requirements

### Requirement: Persistência do histórico privado

O sistema SHALL manter uma biblioteca visual para a cliente autorizada, onde ela retoma apenas galerias derivadas, pastas liberadas, seleções, pedidos e histórico sem acesso ao acervo-mãe. A interface SHALL identificar fotos já compradas e preservar acesso a histórico permitido após a expiração da seleção.

#### Scenario: Biblioteca vazia

- **WHEN** a cliente autenticada não possui galeria derivada ativa nem entrega histórica
- **THEN** a interface mostra estado vazio claro sem sugerir ou revelar galerias de terceiros

#### Scenario: Nova pasta liberada

- **WHEN** o fotógrafo libera uma nova pasta autorizada para a cliente
- **THEN** a biblioteca ou galeria apresenta a nova rodada separadamente das fotos já revisadas

#### Scenario: Histórico após expiração

- **WHEN** o prazo de seleção de uma galeria privada expira
- **THEN** a cliente continua acessando seus pedidos, entregas e identificação de fotos já compradas, sem poder criar seleção fora das regras de reativação

### Requirement: Interface da cliente orientada pelo backend

O sistema SHALL renderizar biblioteca, pastas, propriedade, permissões, prazo, interações, estados das fotos e histórico da cliente a partir de respostas autorizadas do backend. O frontend SHALL NOT inferir vínculo por link, telefone informado ou estado local.

#### Scenario: Permissão alterada

- **WHEN** o fotógrafo altera acesso, prazo, permissões ou liberação de uma galeria derivada
- **THEN** a cliente vê o novo estado retornado pelo backend sem o frontend conceder ou preservar permissão localmente

#### Scenario: Galeria de outra responsável

- **WHEN** uma cliente possui o URL ou identificador de uma galeria pertencente a outra responsável
- **THEN** a interface recebe somente resposta de acesso negado e não exibe metadados, fotos, favoritos, comentários ou pedidos dessa galeria
