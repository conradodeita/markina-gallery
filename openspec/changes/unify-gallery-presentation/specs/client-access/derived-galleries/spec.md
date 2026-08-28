## MODIFIED Requirements

### Requirement: Interface da cliente orientada pelo backend

O sistema SHALL renderizar a galeria privada da cliente usando a mesma composição visual base da prévia do fotógrafo, adaptada ao conjunto de pastas liberadas, fotos atribuídas, permissões e interações retornadas pelo backend. A composição compartilhada SHALL NOT fazer o frontend inferir vínculo, revelar a galeria-mãe ou exibir conteúdo não autorizado.

#### Scenario: Cliente abre galeria autorizada

- **WHEN** a cliente autenticada abre uma galeria privada ativa
- **THEN** ela vê capa, navegação por pastas, grade e visualizador na mesma hierarquia visual da prévia do fotógrafo, restritos às suas prévias autorizadas

#### Scenario: Conteúdo não liberado

- **WHEN** uma pasta ou foto não está liberada para a cliente
- **THEN** a composição compartilhada não a apresenta nem indica sua existência
