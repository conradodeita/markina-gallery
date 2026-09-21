## MODIFIED Requirements

### Requirement: Exclusão segura de pasta
O sistema SHALL permitir excluir pasta de conteúdo vazia, em preparação ou liberada e fotos avulsas, preservando histórico textual antes da remoção. Pagamentos pendentes, comunicados ou confirmados SHALL NOT bloquear a exclusão nem sofrer transição financeira automática.

#### Scenario: Pasta com estados mistos
- **WHEN** o fotógrafo confirma exclusão de pasta contendo fotos selecionadas e compradas
- **THEN** toda a pasta é removida, os movimentos e pedidos permanecem com seus nomes e estados e outras pastas não são alteradas

#### Scenario: Foto com mídia histórica
- **WHEN** uma foto é excluída
- **THEN** cópias operacionais e históricas dessa foto são removidas com limpeza confinada e retomável e os itens comerciais preservam seu nome

#### Scenario: Remoção de preparação abandonada
- **WHEN** o fotógrafo confirma a remoção de uma pasta vazia em preparação
- **THEN** o sistema remove somente a pasta, registra auditoria e preserva outros acervos
