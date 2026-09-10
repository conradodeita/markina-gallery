## Purpose

Centralizar a conferência de seleções, pedidos, pagamentos e mensagens em uma operação financeira por cliente e galeria, preservando decisões auditáveis e estatísticas coerentes.

## ADDED Requirements

### Requirement: Área unificada de vendas e pagamentos

O sistema SHALL apresentar uma única área administrativa de Vendas e pagamentos, agrupada por cliente e separada por Galeria pública e pedido. A área SHALL distinguir seleção sem pedido, aguardando pagamento, pagamento comunicado, pagamento confirmado, pagamento não localizado e falha de mensagem.

#### Scenario: Cliente compra em várias galerias

- **WHEN** a mesma cliente possui pedidos em Galerias públicas diferentes
- **THEN** a interface mostra cada galeria e seus pedidos separadamente, sem combinar itens, valores, decisões ou prazos

#### Scenario: Fotos de várias pastas

- **WHEN** um pedido contém fotos de várias pastas da mesma galeria
- **THEN** o sistema mantém um único pedido daquela galeria e permite conferir seus itens agrupados por pasta

### Requirement: Confirmação condicionada à comunicação

O sistema SHALL disponibilizar a confirmação administrativa somente quando a cliente tiver comunicado o pagamento de um pedido pendente. Seleção sem pedido e pedido sem comunicação SHALL permanecer informativos e SHALL NOT oferecer confirmação financeira.

#### Scenario: Pagamento comunicado

- **WHEN** existe comunicação pendente de revisão para o pedido
- **THEN** o fotógrafo vê valor, galeria, data, itens e a ação `Confirmar pagamento`

#### Scenario: Cliente ainda não comunicou

- **WHEN** existe seleção ou pedido pendente sem comunicação de pagamento
- **THEN** o sistema apresenta o estado correspondente sem permitir confirmar o pagamento

### Requirement: Confirmação independente da mensagem

O sistema SHALL persistir a confirmação, recalcular compras e estatísticas e registrar auditoria antes de processar a mensagem WhatsApp. Falha, indisponibilidade ou atraso do transporte SHALL NOT reverter nem ocultar a confirmação financeira.

#### Scenario: WhatsApp falha após confirmação

- **WHEN** o fotógrafo confirma o pagamento e a mensagem não é entregue
- **THEN** o pedido permanece confirmado, os indicadores financeiros são atualizados e a interface oferece retentativa da mensagem separadamente

### Requirement: Correção administrativa sem notificação

O sistema SHALL permitir ao fotógrafo corrigir uma confirmação equivocada de forma explícita, idempotente e auditável. A correção SHALL retornar o pedido e sua comunicação a `Pagamento comunicado — aguardando revisão`, retirar seus itens das compras confirmadas e das estatísticas confirmadas e SHALL NOT enfileirar mensagem para a cliente.

#### Scenario: Correção válida

- **WHEN** o fotógrafo confirma a correção de um pagamento anteriormente confirmado
- **THEN** o backend preserva o histórico da decisão anterior, reabre a revisão e recalcula os agregados sem criar entrega WhatsApp

#### Scenario: Correção repetida

- **WHEN** a mesma correção é enviada novamente
- **THEN** o sistema devolve o estado já corrigido sem duplicar auditoria, estatística ou outro efeito

### Requirement: Template global no contexto da decisão

O sistema SHALL mostrar no contexto da confirmação uma prévia do template global vigente e um atalho de edição que informe claramente que a alteração afeta futuras confirmações de todas as clientes. O pedido SHALL registrar qual conteúdo foi renderizado para sua entrega.

#### Scenario: Fotógrafo abre uma comunicação

- **WHEN** a confirmação está disponível
- **THEN** a interface apresenta a prévia da mensagem global e o atalho para sua configuração sem criar template por galeria

### Requirement: Estado comercial nos cards

O sistema SHALL projetar nos cards da Galeria pública e privada o estado comercial autoritativo e contagens coerentes de fotos no acervo privado, fotos selecionadas e fotos compradas.

#### Scenario: Comunicação recebida

- **WHEN** a cliente comunica o pagamento
- **THEN** seus cards administrativos mostram `Pagamento comunicado` e conduzem ao pedido pendente de decisão

#### Scenario: Pagamento corrigido

- **WHEN** uma confirmação é corrigida
- **THEN** os cards deixam de contar as fotos como compradas e voltam a mostrar `Pagamento comunicado`

