# Spec Delta

## MODIFIED Requirements

### Requirement: Liberação de lote para galerias privadas

O sistema SHALL permitir ao fotógrafo liberar uma pasta concluída somente após definir se ela é comum a todas as clientes vinculadas ou restrita a uma lista não vazia de clientes autorizadas. A liberação SHALL preservar a separação entre rodadas de fotos e registrar o público efetivo.

#### Scenario: Lote concluído

- **WHEN** o fotógrafo libera uma pasta pronta para todas as clientes vinculadas
- **THEN** cada cliente autorizada vê a nova pasta na próxima consulta à mesma galeria

#### Scenario: Pasta restrita concluída

- **WHEN** o fotógrafo libera uma pasta pronta para clientes escolhidas
- **THEN** somente as escolhidas veem a nova rodada; uma lista vazia não libera a pasta

### Requirement: Exclusão segura de pasta

O sistema SHALL permitir exclusão administrativa de pasta vazia ou em preparação quando não atingir vínculos ou histórico protegido. Pasta liberada com compra confirmada SHALL permanecer protegida; remover uma atribuição SHALL NOT apagar registros comerciais confirmados.

#### Scenario: Remoção de preparação abandonada

- **WHEN** o fotógrafo confirma a remoção de uma pasta vazia em preparação
- **THEN** o sistema a remove, registra auditoria e não altera acervos autorizados
