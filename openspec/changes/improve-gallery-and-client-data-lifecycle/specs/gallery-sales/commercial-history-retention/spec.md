## Purpose

Preservar o histórico comercial e as entregas autorizadas de forma independente das galerias e mídias operacionais que lhes deram origem.

## ADDED Requirements

### Requirement: Histórico comercial independente

O sistema SHALL manter pedidos, pagamentos, itens, quantidades, valores, identidade histórica do cliente, identificação histórica da galeria e eventos de confirmação de forma independente da existência posterior da galeria, pasta, foto ou vínculo operacional. Registros comerciais confirmados SHALL ser imutáveis, exceto por eventos corretivos auditados que não apaguem o estado anterior.

#### Scenario: Exclusão da galeria após pagamento

- **WHEN** uma galeria com compra paga é excluída
- **THEN** fotógrafo e cliente continuam vendo a compra com os mesmos itens, valores, datas, situação de pagamento e identificação histórica

#### Scenario: Cliente é desvinculada após compra

- **WHEN** uma cliente é desvinculada da galeria que originou sua compra
- **THEN** o cadastro e o histórico comercial permanecem associados à cliente sem restabelecer acesso à galeria operacional

#### Scenario: Consulta administrativa histórica

- **WHEN** o fotógrafo consulta vendas de uma galeria operacional já removida
- **THEN** o sistema apresenta o registro histórico identificado como galeria removida e não depende de relações operacionais inexistentes

### Requirement: Evidência visual e entrega histórica

O sistema SHALL preservar, para cada item comprado, metadados imutáveis, uma prévia histórica mínima protegida e a entrega final ou sua referência segura, em armazenamento separado da mídia operacional da galeria. O sistema SHALL NOT reter fotos não compradas nem copiar todos os originais sob a justificativa de histórico comercial. A retenção SHALL ser configurável e documentada sem inventar nesta change prazo legal, e a PII SHALL ser removida ou anonimizada quando permitido sem apagar registros contábeis ou de auditoria que precisem permanecer.

#### Scenario: Item comprado permanece identificável

- **WHEN** o arquivo operacional de uma foto comprada é removido com a galeria
- **THEN** o histórico continua exibindo a identificação visual autorizada do item sem depender do caminho operacional removido

#### Scenario: Foto não comprada é removida

- **WHEN** a galeria excluída contém uma foto sem item comercial preservável
- **THEN** o sistema apaga o original e seus derivados e não cria cópia no armazenamento histórico

#### Scenario: Acesso à mídia histórica

- **WHEN** cliente ou fotógrafo solicita mídia histórica de um item comprado
- **THEN** o backend autoriza a solicitação pelo histórico comercial e entrega somente o derivado ou arquivo permitido para aquele papel

#### Scenario: Referência final substitui cópia de original

- **WHEN** a entrega final permanece disponível por referência segura e verificável
- **THEN** o sistema preserva essa referência e a prévia histórica mínima sem duplicar o original somente para compor histórico

#### Scenario: Solicitação de privacidade

- **WHEN** existe solicitação válida para remoção ou anonimização de dados pessoais
- **THEN** o sistema minimiza a PII permitida e preserva somente os campos comerciais e de auditoria cuja retenção continue necessária

### Requirement: Política comercial para remoção operacional

O sistema SHALL decidir remoção de seleção, referência, vínculo ou galeria pelo estado comercial. Carrinho sem pedido persistido SHALL poder ser descartado. Pedido pendente sem comunicação de pagamento SHALL ser cancelado com auditoria antes da remoção. Pedido com pagamento comunicado ou `pending_review` SHALL bloquear a remoção afetada até decisão administrativa. Pedido confirmado SHALL permitir remoção operacional somente depois de materializados e verificados snapshots, prévia histórica mínima e entrega ou referência final.

#### Scenario: Carrinho ainda não virou pedido

- **WHEN** a cliente remove a última seleção que existe apenas em carrinho não persistido como pedido
- **THEN** o sistema descarta o carrinho e aplica o ciclo de vida operacional sem criar histórico financeiro fictício

#### Scenario: Pedido pendente sem pagamento comunicado

- **WHEN** uma operação de remoção alcança pedido pendente sem comunicação de pagamento
- **THEN** o sistema registra o cancelamento auditado antes de remover os estados operacionais afetados

#### Scenario: Pagamento comunicado aguarda revisão

- **WHEN** uma operação de remoção alcança pedido com pagamento comunicado ou `pending_review`
- **THEN** o sistema bloqueia a remoção afetada, informa o motivo e mantém os dados disponíveis para decisão administrativa

#### Scenario: Pedido confirmado

- **WHEN** uma operação de remoção alcança pedido confirmado
- **THEN** o sistema só remove as entidades operacionais depois de verificar o snapshot e a mídia histórica mínima autorizada

### Requirement: Auditoria da limpeza operacional

O sistema SHALL registrar quem iniciou a exclusão, o instante, os totais previstos, os totais removidos, os vínculos desfeitos, os históricos preservados e qualquer falha, sem armazenar segredos nem duplicar dados pessoais desnecessários.

#### Scenario: Exclusão concluída

- **WHEN** a limpeza operacional termina com sucesso
- **THEN** o registro de auditoria permite comprovar o escopo removido e o histórico preservado sem reconstituir a galeria ativa

#### Scenario: Exclusão falha

- **WHEN** uma etapa de limpeza não pode ser concluída
- **THEN** a auditoria identifica a etapa e o erro, mantendo a operação retomável e sem declarar a galeria como excluída com sucesso
