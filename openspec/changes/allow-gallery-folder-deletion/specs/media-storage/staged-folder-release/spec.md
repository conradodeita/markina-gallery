## MODIFIED Requirements

### Requirement: Exclusão segura de pasta
O sistema SHALL permitir ao administrador excluir uma pasta de conteúdo pública ou própria de galeria privada, vazia ou com fotos, inclusive liberada, após confirmação explícita na interface. O sistema SHALL aplicar a política comercial vigente a todas as fotos e preservar histórico e mídia de compras confirmadas antes de remover os dados operacionais. Um bloqueio comercial SHALL preservar toda a pasta. A operação MUST validar escopo, remover vínculos e registros biométricos das fotos afetadas, limpar apenas arquivos do storage autorizado após commit e registrar auditoria.

#### Scenario: Remoção de preparação abandonada
- **WHEN** o fotógrafo confirma a remoção de uma pasta vazia em preparação
- **THEN** o sistema a remove e registra auditoria sem alterar outras pastas

#### Scenario: Pasta liberada com conteúdo
- **WHEN** o administrador confirma excluir uma pasta liberada com fotos sem bloqueio comercial
- **THEN** o sistema remove a pasta e suas fotos operacionais, limpa vínculos e atualiza a interface mantendo outras pastas

#### Scenario: Pagamento comunicado
- **WHEN** qualquer foto da pasta pertence a uma compra com pagamento aguardando decisão
- **THEN** nenhuma foto nem a pasta é removida e a interface apresenta a razão do bloqueio

#### Scenario: Pasta própria privada
- **WHEN** o administrador exclui uma pasta própria de galeria privada mutável
- **THEN** a operação se limita ao conteúdo dessa pasta, inclusive quando a origem pública já foi excluída

#### Scenario: Histórico confirmado
- **WHEN** a pasta contém fotos compradas com pagamento confirmado
- **THEN** a exclusão operacional só prossegue após preservar o histórico e sua mídia conforme a política comercial vigente
