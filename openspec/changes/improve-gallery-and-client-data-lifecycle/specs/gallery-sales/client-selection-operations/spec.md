## MODIFIED Requirements

### Requirement: Ficha individual de seleção e compra

O sistema SHALL fornecer ao fotógrafo uma ficha individual por galeria privada derivada com cliente proprietária, Galeria pública de origem, prazo, estado de acesso, quantidade de fotos disponíveis, quantidade selecionada, quantidade comprada, estado comercial, totais e datas operacionais. A ficha SHALL distinguir `DerivedGalleryPhoto` ou referência disponível de `PhotoSelection` e SHALL indicar a procedência `admin`, `client` ou origem futura autorizada sem apresentar foto administrativa como seleção de compra.

#### Scenario: Fotógrafo abre uma seleção

- **WHEN** o fotógrafo seleciona uma cliente na ficha de uma Galeria pública
- **THEN** o sistema apresenta somente as fotos disponíveis, seleções e compras daquela cliente, em contadores distintos e sem combinar dados de outras clientes

#### Scenario: Galeria administrativa sem seleção

- **WHEN** a galeria privada possui fotos disponíveis de origem `admin`, mas a cliente não selecionou nenhuma
- **THEN** a ficha mostra disponibilidade maior que zero, seleção igual a zero e mantém a galeria operacional

### Requirement: Imutabilidade comercial após confirmação

O sistema SHALL manter congeladas as fotos, valores e regras de um pedido confirmado. A cliente poderá realizar um novo pedido distinto de fotos ainda elegíveis enquanto sua galeria estiver ativa. Remover seleção ou referência operacional SHALL descartar carrinho sem pedido, cancelar com auditoria pedido pendente sem pagamento comunicado, bloquear pedido com pagamento comunicado ou `pending_review` e, em pedido confirmado, ocorrer somente após materialização e verificação do histórico comercial independente.

#### Scenario: Cliente compra fotos adicionais

- **WHEN** uma cliente com pedido confirmado seleciona novas fotos em galeria ainda ativa
- **THEN** o sistema cria um novo fluxo de pedido sem alterar o pedido já confirmado

#### Scenario: Pagamento aguarda revisão

- **WHEN** uma remoção alcança foto relacionada a pagamento comunicado ou `pending_review`
- **THEN** o backend bloqueia a mutação afetada e mantém seleção, pedido e evidências disponíveis para decisão administrativa

#### Scenario: Remoção após confirmação

- **WHEN** uma referência operacional de pedido confirmado será removida
- **THEN** o sistema verifica snapshots, prévia histórica mínima e entrega ou referência final antes de concluir a remoção sem alterar o pedido
