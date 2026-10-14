# media-storage/staged-folder-release Specification

## Purpose
Definir pastas como lotes de fotos preparados e liberados de modo controlado, evitando que clientes recebam fotos incompletas ou rodadas posteriores por engano.

## Requirements

### Requirement: Pasta preparada antes da liberação
O sistema SHALL manter cada pasta de um acervo em estado de preparação até que o fotógrafo conclua seu conteúdo e a libere explicitamente. Fotos em preparação SHALL permanecer exclusivas da área administrativa.

#### Scenario: Upload em andamento
- **WHEN** o fotógrafo adiciona JPEGs a uma pasta ainda em preparação
- **THEN** ele vê progresso, sucesso ou falha de cada arquivo e nenhuma cliente vê a pasta ou suas fotos

### Requirement: Liberação de lote para galerias privadas

O sistema SHALL permitir ao fotógrafo liberar uma pasta concluída somente após definir se ela é comum a todas as clientes vinculadas ou restrita a uma lista não vazia de clientes autorizadas. A liberação SHALL preservar a separação entre rodadas de fotos e registrar o público efetivo.

#### Scenario: Lote concluído

- **WHEN** o fotógrafo libera uma pasta pronta para todas as clientes vinculadas
- **THEN** cada cliente autorizada vê a nova pasta na próxima consulta à mesma galeria

#### Scenario: Pasta restrita concluída

- **WHEN** o fotógrafo libera uma pasta pronta para clientes escolhidas
- **THEN** somente as escolhidas veem a nova rodada; uma lista vazia não libera a pasta

### Requirement: Nova rodada em pasta distinta
O sistema SHALL exigir uma nova pasta para fotos acrescentadas após a liberação de um lote. O sistema SHALL NOT inserir essas fotos silenciosamente na pasta já liberada.

#### Scenario: Fotos posteriores do evento
- **WHEN** o fotógrafo possui fotos adicionais depois de liberar uma pasta
- **THEN** ele cria ou seleciona uma nova pasta em preparação antes de disponibilizá-la em uma nova rodada

### Requirement: Exclusão segura de pasta

O sistema SHALL permitir exclusão administrativa de pasta vazia ou em preparação quando não atingir vínculos ou histórico protegido. Pasta liberada com compra confirmada SHALL permanecer protegida; remover uma atribuição SHALL NOT apagar registros comerciais confirmados.

#### Scenario: Remoção de preparação abandonada

- **WHEN** o fotógrafo confirma a remoção de uma pasta vazia em preparação
- **THEN** o sistema a remove, registra auditoria e não altera acervos autorizados
