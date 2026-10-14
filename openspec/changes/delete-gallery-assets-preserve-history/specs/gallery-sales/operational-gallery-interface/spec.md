## MODIFIED Requirements

### Requirement: Exclusão segura de galeria privada
O sistema SHALL permitir excluir galeria com fotos, seleções ou pedidos mediante confirmação explícita. A exclusão pública SHALL remover pastas, uploads e referências privadas dependentes, fotos e prévias, preservando apenas histórico textual e estados financeiros. A exclusão privada SHALL preservar arquivos públicos compartilhados com outros acervos.

#### Scenario: Histórico de compra preservado
- **WHEN** o fotógrafo confirma a exclusão de galeria com compra confirmada
- **THEN** a galeria e seu acervo deixam as listas e o acesso operacional
- **AND** nomes das fotos, valores e estado confirmado permanecem no histórico sem exigir cópias de mídia

#### Scenario: Galeria privada com referências
- **WHEN** o fotógrafo exclui somente uma galeria privada
- **THEN** seus arquivos próprios são removidos e referências públicas são desvinculadas sem apagar originais compartilhados
