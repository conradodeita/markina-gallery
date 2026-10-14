## Purpose

Permitir que uma cliente revise fotos de várias galerias e pastas e comunique um único PIX, mantendo valores, autorização e rastreabilidade dos pedidos de cada galeria.

## ADDED Requirements

### Requirement: Revisão consolidada das seleções

O sistema SHALL apresentar todas as seleções persistidas e autorizadas da cliente em uma revisão única, agrupadas por galeria e identificadas por pasta quando aplicável. Cada grupo SHALL mostrar fotos, quantidade, subtotal e impedimentos relevantes. O total geral SHALL somar os subtotais calculados pelo servidor em centavos, preservando o escopo das regras comerciais vigentes de cada pedido, sem aplicar faixas entre galerias.

#### Scenario: Seleção em várias galerias e pastas
- **WHEN** a cliente seleciona fotos em duas galerias e em duas pastas liberadas de uma delas
- **THEN** a revisão apresenta todas as fotos sob os respectivos nomes de galeria e pasta, com subtotais e um total geral
- **AND** oferece uma única área de pagamento para a seleção consolidada

#### Scenario: Uma galeria não pode ser finalizada
- **WHEN** uma seleção está expirada, indisponível ou sem cotação válida
- **THEN** a revisão identifica o impedimento sem descartar silenciosamente fotos nem apresentar um total parcial como total pagável
- **AND** permite revisar ou remover explicitamente a seleção impedida antes de preparar o pagamento das restantes

### Requirement: Pagamento PIX único com origem preservada

O sistema SHALL vincular um único pagamento manual ao conjunto de pedidos da mesma cliente, incluindo o caso de uma só galeria. O pagamento SHALL preservar um snapshot de valor total, instruções PIX e composição por pedido. QR Code, copia-e-cola e `Informar pagamento` SHALL se referir ao conjunto revisado. Os pedidos SHALL manter origem, itens, preços, regras e operação de produção/entrega próprios. O sistema SHALL NOT confirmar recebimento bancário pela exibição do QR Code ou pela comunicação da cliente.

#### Scenario: Comunicação consolidada
- **WHEN** a cliente informa o pagamento da revisão válida de duas galerias
- **THEN** o sistema registra uma comunicação para o valor total e congela todos os pedidos vinculados na mesma operação
- **AND** remove do carrinho somente as seleções incluídas e apresenta uma compra com estado `Pagamento informado`

#### Scenario: Instruções de pagamento preservadas
- **WHEN** a configuração PIX global muda depois da preparação de um pagamento
- **THEN** o pagamento preparado continua associado ao seu snapshot e novas preparações independentes usam a configuração vigente
- **AND** o histórico não é reescrito pela alteração administrativa

#### Scenario: Código configurado possui valor incompatível
- **WHEN** o código PIX configurado contém um valor fixo diferente do total da revisão
- **THEN** o sistema impede apresentar esse código como pagamento válido daquela revisão e mantém a seleção, com mensagem recuperável

#### Scenario: Rascunhos legados possuem instruções incompatíveis
- **WHEN** a migração encontra checkouts já preparados para a mesma cliente com snapshots PIX incompatíveis entre si ou com a preparação agrupada
- **THEN** o sistema preserva as instruções iniciadas e informa o impedimento de agrupamento, sem escolher recebedor arbitrariamente
- **AND** mantém acesso ao detalhe legado para recuperação, sem combinar pagamentos históricos nem descartar seleções

### Requirement: Revisão consistente e comunicação atômica

O sistema SHALL verificar no servidor a identidade da cliente, propriedade dos pedidos, seleção, elegibilidade, prazo, cotação e versão da revisão antes de aceitar a comunicação. Preparação, comunicação e decisões financeiras SHALL ser idempotentes e não produzir duplicidade sob repetição ou concorrência. Uma falha em qualquer componente SHALL impedir efeitos financeiros ou congelamento parcial do conjunto.

#### Scenario: Carrinho muda em outra aba
- **WHEN** a cliente tenta comunicar pagamento de uma revisão cuja seleção ou cotação mudou
- **THEN** o sistema exige atualizar a revisão e conferir o total antes de comunicar
- **AND** não congela automaticamente a composição diferente daquela apresentada

#### Scenario: Reenvio depois de falha de conexão
- **WHEN** a comunicação já foi registrada e a mesma solicitação é reenviada
- **THEN** o sistema retorna a mesma compra sem criar pedidos, comunicações ou eventos de notificação duplicados

#### Scenario: Falha durante gravação
- **WHEN** uma das gravações necessárias para comunicar o conjunto falha
- **THEN** nenhum pedido do conjunto fica parcialmente comunicado, congelado ou removido do carrinho

#### Scenario: Identificador de outra cliente
- **WHEN** uma cliente tenta consultar ou comunicar pagamento de um conjunto ou pedido alheio
- **THEN** o sistema nega acesso sem revelar fotos, valores, PIX ou metadados alheios

### Requirement: Decisão financeira única e compatibilidade histórica

O sistema SHALL permitir ao fotógrafo confirmar, recusar e corrigir a decisão do pagamento agrupado de forma atômica, refletindo o estado financeiro nos pedidos vinculados. Atalhos de pedidos integrantes SHALL encaminhar para essa decisão conjunta e identificar seu alcance. Pedidos antigos sem agrupamento SHALL continuar operáveis e visíveis sem combinação retroativa. A contabilização SHALL NOT somar simultaneamente o total do grupo e seus subtotais como receitas diferentes.

#### Scenario: Confirmação a partir de uma galeria
- **WHEN** o fotógrafo abre o atalho de confirmação de um pedido que pertence a um pagamento de duas galerias
- **THEN** a interface identifica o valor total e todas as galerias abrangidas
- **AND** uma confirmação válida atualiza o grupo e os dois pedidos na mesma transação

#### Scenario: Recusa e correção
- **WHEN** o fotógrafo recusa ou corrige uma decisão de pagamento agrupado
- **THEN** os pedidos vinculados refletem a mesma decisão financeira com auditoria do ator e motivo conforme as regras existentes
- **AND** a correção permanece silenciosa nos canais externos, preservando o comportamento vigente

#### Scenario: Aviso de pagamento consolidado
- **WHEN** um pagamento agrupado é informado, confirmado ou recusado
- **THEN** cada canal habilitado recebe no máximo um evento lógico daquele tipo para o grupo, sujeito aos mecanismos existentes de entrega e repetição
- **AND** o aviso aponta para o detalhe autorizado da compra agrupada

#### Scenario: Pedido anterior à mudança
- **WHEN** a cliente ou o fotógrafo abre um pedido legado sem agrupamento
- **THEN** seus valores, status, instruções e ações permanecem disponíveis conforme as regras anteriores

### Requirement: Compra informada não é carrinho editável

O sistema SHALL manter como carrinho a seleção cujo pagamento ainda não foi comunicado, mesmo após preparar o QR Code. A comunicação SHALL mover a compra para o histórico imediatamente. Novas seleções elegíveis SHALL formar um novo carrinho sem modificar compras informadas ou confirmadas. Recusas SHALL permanecer identificáveis no histórico, preservando o fluxo existente de tratamento sem restaurar ou duplicar silenciosamente seleções.

#### Scenario: Cliente abandona a revisão
- **WHEN** a cliente visualiza o QR Code, sai sem informar pagamento e retorna autenticada
- **THEN** pode retomar a seleção no carrinho e conferir sua situação atual
- **AND** a simples visualização do PIX não cria uma compra no histórico

#### Scenario: Compra adicional
- **WHEN** a cliente seleciona outras fotos elegíveis após informar um pagamento
- **THEN** as novas fotos aparecem no carrinho e a compra anterior permanece separada e inalterada em `Compras`

#### Scenario: Cliente remove toda a seleção antes de informar pagamento
- **WHEN** a cliente remove explicitamente as últimas fotos de um carrinho preparado
- **THEN** o sistema descarta os rascunhos vazios e o agrupamento ainda não comunicado
- **AND** uma revisão antiga não pode ser comunicada e nenhuma compra histórica é modificada
