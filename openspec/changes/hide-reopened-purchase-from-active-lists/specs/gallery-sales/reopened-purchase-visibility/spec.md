# Spec Delta

## ADDED Requirements

### Requirement: Tentativa reaberta separada da compra ativa

O sistema SHALL retirar de Compras e da lista principal de Vendas e pagamentos somente a tentativa de cartão em exception com reabertura auditada e sem evidência financeira posterior que exija conferência. As fotos SHALL permanecer no carrinho editável e a cliente SHALL poder manter, alterar ou remover toda a seleção. MUST NOT apagar compra, pedidos, snapshots, tentativas, auditoria ou credenciais históricas. Esta decisão substitui a exibição anterior da tentativa reaberta em Compras.

#### Scenario: Reabertura seguida de seleção vazia
- **WHEN** o fotógrafo reabre e a cliente remove todas as fotos
- **THEN** Compras não mostra aquela tentativa como compra e o carrinho permanece vazio
- **AND** o histórico interno permanece intacto sem restaurar fotos automaticamente

#### Scenario: Reabertura com nova compra
- **WHEN** a cliente mantém as fotos ou faz nova escolha e inicia outro pagamento
- **THEN** somente a nova compra elegível aparece como ativa
- **AND** a tentativa antiga não altera a nova compra nem cria receita

#### Scenario: Ausência de auditoria ou compra confirmada
- **WHEN** não há reabertura auditada ou o pagamento está confirmado
- **THEN** esta regra não oculta o registro

### Requirement: Histórico administrativo explícito e isolado

O fotógrafo SHALL consultar as tentativas reabertas por filtro explícito em Vendas e pagamentos com rótulo Tentativa encerrada por reabertura. Listagem e totais principais SHALL excluí-las; filtro, exportação e paginação SHALL compartilhar a classificação e as restrições da própria conta. Histórico MUST NOT permitir confirmar, entregar ou reabrir novamente a tentativa encerrada. Inventários e proteções de exclusão SHALL conservar todos os registros.

#### Scenario: Consulta ao histórico
- **WHEN** o fotógrafo seleciona o filtro de tentativas reabertas
- **THEN** vê somente as tentativas auditadas encerradas da própria conta
- **AND** a lista principal e suas contagens não as tratam como pendência ativa

### Requirement: Recibos tardios preservados

Recibos `queued`, `processing` ou `verified` SHALL permanecer visíveis após reabertura. Recibos `ignored` ou `failed` SHALL permanecer visíveis se o instante efetivo (`processed_at`, ou `created_at` quando não houver processamento) for igual ou posterior ao evento auditado. Um recibo terminal anterior, sem outra evidência, não exige conferência.

#### Scenario: Recibo terminal anterior à reabertura
- **WHEN** existe somente um recibo `ignored` ou `failed` cujo instante efetivo antecede a reabertura
- **THEN** a tentativa permanece histórica e não reaparece para conferência

### Requirement: Sinais financeiros exigem conferência

NSU, `confirmed_at` e estados financeiros incompatíveis SHALL permanecer visíveis após reabertura. Evidência não confirmada SHALL indicar `Conferência após reabertura`. O sistema MUST NOT expor URL antiga, confirmar pedido cancelado, alterar compra nova nem inferir cancelamento remoto pela remoção de fotos.

#### Scenario: Evidência chega após esvaziar o carrinho
- **WHEN** chega evidência financeira da tentativa reaberta depois da remoção de fotos
- **THEN** a ocorrência reaparece para conferência nas listas do cliente e fotógrafo
- **AND** a seleção continua vazia e os pedidos antigos continuam cancelados

#### Scenario: Resposta antiga sem evidência financeira
- **WHEN** somente uma resposta de criação retorna uma URL após reabertura
- **THEN** a tentativa permanece histórica sem checkout retomável e sem restaurar seleção
