## MODIFIED Requirements

### Requirement: Exclusão em massa elegível

O sistema SHALL permitir selecionar várias fotos operacionais e solicitar exclusão com uma única confirmação e inventário, inclusive em seleções superiores a 2.000 fotos e quando a quantidade selecionada exceder o limite de transporte de uma requisição. Nesse caso, o sistema SHALL executar lotes seguros sem exigir novas confirmações, SHALL preservar o limite defensivo da API e SHALL consolidar o resultado da operação inteira. A operação SHALL aplicar a política comercial do backend: fotos sem pedido impeditivo podem ser removidas; pedido pendente sem pagamento comunicado é cancelado com auditoria; pagamento comunicado ou `pending_review` bloqueia a foto afetada; item confirmado somente perde sua referência operacional após preparação do histórico mínimo. A exclusão SHALL informar individualmente removidas, preservadas e bloqueadas. Se um lote falhar após remoções confirmadas, o sistema SHALL atualizar o estado visível, informar o resultado parcial e permitir repetição segura somente para as fotos remanescentes.

#### Scenario: Exclusão parcial protegida

- **WHEN** o fotógrafo seleciona fotos elegíveis e fotos relacionadas a estados comerciais impeditivos
- **THEN** o sistema exclui somente as elegíveis, preserva as bloqueadas e informa o motivo de cada resultado

#### Scenario: Foto confirmada com histórico preparado

- **WHEN** a foto integra pedido confirmado e sua evidência mínima e entrega já foram verificadas
- **THEN** a operação pode remover a mídia operacional sem alterar item, valores, cliente ou acesso histórico autorizado

#### Scenario: Seleção superior a duas mil fotos

- **WHEN** o fotógrafo confirma uma seleção superior a 2.000 fotos, excedendo o máximo aceito por uma requisição da API
- **THEN** o sistema processa a seleção em lotes seguros, solicita uma única confirmação e apresenta os totais consolidados da operação

#### Scenario: Falha depois de lote concluído

- **WHEN** um lote posterior falha depois que ao menos um lote anterior já confirmou remoções
- **THEN** o sistema informa quantas fotos foram removidas, atualiza a pasta e permite repetir a ação sem tentar restaurar ou ocultar o resultado parcial
