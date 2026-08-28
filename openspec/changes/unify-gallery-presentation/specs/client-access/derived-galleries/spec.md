## MODIFIED Requirements

### Requirement: Interface da cliente orientada pelo backend

O sistema SHALL renderizar biblioteca, pastas, propriedade, permissões, prazo, interações, estados das fotos e histórico da cliente a partir de respostas autorizadas do backend. A galeria privada SHALL usar a mesma composição visual base da prévia do fotógrafo, adaptada ao conjunto de pastas liberadas e fotos atribuídas. A composição compartilhada SHALL NOT fazer o frontend inferir vínculo, revelar a galeria-mãe ou exibir conteúdo não autorizado.

#### Scenario: Permissão alterada

- **WHEN** o fotógrafo altera acesso, prazo, permissões ou liberação de uma galeria derivada
- **THEN** a cliente vê o novo estado retornado pelo backend sem o frontend conceder ou preservar permissão localmente

#### Scenario: Galeria de outra responsável

- **WHEN** uma cliente possui o URL ou identificador de uma galeria pertencente a outra responsável
- **THEN** a interface recebe somente resposta de acesso negado e não exibe metadados, fotos, favoritos, comentários ou pedidos dessa galeria

#### Scenario: Cliente abre galeria autorizada

- **WHEN** a cliente autenticada abre uma galeria privada ativa
- **THEN** ela vê capa, navegação por pastas, grade e visualizador na mesma hierarquia visual da prévia do fotógrafo, restritos às suas prévias autorizadas

#### Scenario: Conteúdo não liberado

- **WHEN** uma pasta ou foto não está liberada para a cliente
- **THEN** a composição compartilhada não a apresenta nem indica sua existência
