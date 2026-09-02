## MODIFIED Requirements

### Requirement: Ficha individual de seleção e compra
O sistema SHALL fornecer ao fotógrafo uma ficha por cliente dentro da galeria privada compartilhada com Galeria pública de origem, prazo, acesso, quantidade disponível, selecionada e comprada, estado comercial, totais e datas. A ficha SHALL separar o acervo comum das interações e compras daquela cliente.

#### Scenario: Fotógrafo abre uma cliente
- **WHEN** o fotógrafo seleciona uma cliente na ficha da privada ou da Galeria pública
- **THEN** o sistema apresenta somente seleção, comentários, pedidos e valores daquela cliente, além das fotos comuns disponíveis

#### Scenario: Fotógrafo abre uma seleção
- **WHEN** o fotógrafo abre a ficha de uma cliente vinculada à privada
- **THEN** o sistema apresenta somente o resumo e a seleção daquela cliente, sem combinar seus dados com os de outros membros

#### Scenario: Privada com vários membros
- **WHEN** duas clientes selecionam quantidades diferentes no mesmo acervo
- **THEN** os cards mostram contagens e totais independentes sem somar ou revelar a atividade entre elas

### Requirement: Imutabilidade comercial após confirmação
O sistema SHALL manter congeladas fotos, parcelas progressivas, valores, economia e regras de cada pedido. Uma cliente poderá realizar novo pedido de fotos ainda elegíveis enquanto sua associação e a privada estiverem ativas; atividade de outro membro SHALL NOT alterar sua elegibilidade ou histórico.

#### Scenario: Cliente compra fotos adicionais
- **WHEN** uma cliente com pedido confirmado seleciona novas fotos na mesma privada
- **THEN** o sistema inicia pedido complementar sem alterar o confirmado e calcula preço somente sobre a nova seleção elegível conforme a regra vigente

#### Scenario: Outro membro compra a mesma foto
- **WHEN** uma segunda cliente seleciona foto comprada por outro membro
- **THEN** o sistema permite seu pedido independente e não revela quem comprou anteriormente

#### Scenario: Pagamento informado
- **WHEN** a cliente aciona `Informar pagamento`
- **THEN** o pedido e sua seleção ficam congelados em análise até decisão administrativa, e novas escolhas seguem fluxo complementar separado
