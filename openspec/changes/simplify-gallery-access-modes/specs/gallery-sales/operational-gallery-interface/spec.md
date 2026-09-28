# Spec Delta

## ADDED Requirements

### Requirement: Dois modos de entrada com público de pastas independente

A interface administrativa SHALL oferecer somente `Padrão` e `Somente convite individual` para criação e alteração explícita do modo de entrada, com `Somente convite individual` como valor inicial de novas galerias. A API SHALL recusar a criação ou escolha explícita de `collective_protected`. A explicação SHALL distinguir entrada por link/OTP de entrada previamente autorizada e informar que ambos os modos mostram pastas comuns e exclusivas atribuídas. A seção SHALL NOT sugerir que o modo ativa ou desativa processamento facial.

#### Scenario: Fotógrafo cria uma galeria

- **WHEN** o fotógrafo abre a criação de galeria
- **THEN** encontra somente os dois modos operacionais, com Somente convite individual inicialmente selecionado

#### Scenario: Chamada antiga tenta escolher Coletivo protegido

- **WHEN** uma chamada administrativa tenta criar galeria ou definir explicitamente o modo `collective_protected`
- **THEN** a API rejeita a entrada sem gravar a alteração nem ampliar permissões

#### Scenario: Edição de registro protegido legado

- **WHEN** o fotógrafo edita outro campo de uma galeria legada `collective_protected` sem escolher novo modo
- **THEN** a interface informa o estado legado e o backend preserva o modo protegido e seus vínculos, sem troca implícita para Padrão ou Somente convite individual

#### Scenario: Mudança explícita de registro protegido legado

- **WHEN** o fotógrafo escolhe um dos dois modos para uma galeria protegida legada
- **THEN** a interface informa que a escolha muda a possibilidade de entrada e navegação; o salvamento aplica somente a escolha explícita, sem promover vínculos pendentes a ativos nem alterar o público das pastas

### Requirement: Pagamento obrigatório configurável na etapa comercial

O editor SHALL oferecer `Pagamento obrigatório?` na etapa 2, inicialmente marcado, preservando cobrança nas galerias existentes. Com cobrança obrigatória, frontend e backend SHALL exigir valor unitário fixo maior que zero ou valores positivos nas faixas aplicáveis da precificação progressiva. Sem cobrança obrigatória, o sistema SHALL preservar a configuração administrativa de preços e permitir seleção sem depender de PIX ou precificação. Preço zero legado SHALL NOT converter a galeria implicitamente para seleção sem cobrança; novas finalizações pagas incompatíveis SHALL exigir revisão da configuração, preservando pedidos congelados.

#### Scenario: Fotógrafo configura cobrança com preço zero

- **WHEN** salva cobrança obrigatória com valor unitário zero
- **THEN** a configuração é rejeitada com orientação para informar valor maior que zero, sem alteração parcial

#### Scenario: Fotógrafo desmarca pagamento obrigatório

- **WHEN** salva a galeria para negociação externa
- **THEN** a cliente pode finalizar sem configurar PIX e os preços e totais daquela seleção ficam ocultos em Galerias, Coleção, Carrinho e Compras

#### Scenario: Compatibilidade de configuração existente

- **WHEN** a migration aditiva é aplicada a galeria existente
- **THEN** o modo continua com cobrança obrigatória e nenhum pedido ou pagamento anterior é convertido

### Requirement: Finalização individual sem cobrança

A cliente SHALL poder usar `Finalizar seleção` para congelar suas fotos autorizadas no modo sem cobrança, dentro do prazo e mediante revisão atual, com resposta explícita de sucesso ou erro. A operação SHALL ser autenticada, idempotente e disponível sem PIX. O histórico em Compras e a ficha do fotógrafo SHALL identificar `Seleção finalizada`, sem pagamento pendente, pagamento confirmado, indicação de gratuidade ou registro de receita. O sistema SHALL preservar snapshot de fotos e modo de cobrança e permitir exportação TXT/CSV e entrega posterior pelo fluxo de link existente. A entrega e suas notificações SHALL aceitar seleção sem cobrança finalizada ou pedido com pagamento confirmado, mantendo todos os controles de identidade e acesso. A finalização SHALL NOT emitir notificações de pagamento informado ou confirmado. Rascunhos pagos ainda editáveis daquela seleção SHALL ser descartados sem afetar pedidos comunicados/congelados. A política explícita existente de retenção de mídia histórica SHALL aplicar seu prazo a partir da finalização para seleções sem cobrança, preservando o tratamento de pedidos pagos.

#### Scenario: Cliente finaliza fotos negociadas externamente

- **WHEN** confirma uma seleção válida sem cobrança e sem PIX configurado
- **THEN** as fotos são congeladas e ficam disponíveis ao fotógrafo para conferência/exportação, com confirmação visível à cliente e histórico sem valores ou pendência financeira

#### Scenario: Fotógrafo entrega seleção finalizada

- **WHEN** disponibiliza o link de entrega para seleção sem cobrança já finalizada
- **THEN** a cliente autorizada pode abrir o link em Compras e o evento existente de entrega segue suas configurações de notificação

#### Scenario: Repetição e revisão obsoleta

- **WHEN** a cliente repete a mesma finalização ou tenta confirmar revisão cujo modo de cobrança mudou
- **THEN** a repetição idempotente não duplica pedidos e a revisão obsoleta é rejeitada sem congelamento parcial

#### Scenario: Mudança posterior de cobrança e fotos adicionais

- **WHEN** o fotógrafo altera o modo após finalização ou a cliente escolhe outras fotos elegíveis dentro do prazo
- **THEN** o pedido finalizado mantém seus itens e modo congelados e fotos adicionais seguem em seleção distinta

#### Scenario: Pedido pago ainda sem confirmação

- **WHEN** um pedido de cobrança obrigatória aguarda confirmação financeira
- **THEN** a nova regra de entrega não libera seu link nem o trata como seleção sem cobrança

### Requirement: Carrinho com modos de cobrança separados

O carrinho SHALL separar seleções sem cobrança dos itens com pagamento obrigatório, com ações independentes `Finalizar seleção` e `Informar pagamento`. Somente itens com cobrança SHALL compor o total e o grupo PIX. Falhas de configuração PIX SHALL NOT impedir a finalização independente de itens sem cobrança. Nenhuma ação SHALL modificar ou finalizar implicitamente o outro grupo.

#### Scenario: Cliente reúne galerias dos dois modos

- **WHEN** revisa fotos de uma galeria com cobrança e outra sem cobrança
- **THEN** encontra ações separadas e o PIX inclui apenas a galeria com cobrança, sem preços/totais para a outra

### Requirement: Mensagem comercial visível na revisão da cliente

A revisão da seleção SHALL apresentar a `Mensagem comercial` não vazia da galeria junto ao grupo de fotos correspondente, tanto no modo pago quanto no modo sem cobrança. O texto SHALL preservar quebras de linha e ser renderizado como texto simples, sem executar HTML. Grupos de galerias diferentes SHALL NOT misturar mensagens, e mensagens vazias SHALL NOT gerar bloco vazio. Pedidos congelados SHALL preservar o snapshot existente da mensagem, independentemente de edição posterior.

#### Scenario: Cliente revisa seleção com mensagem configurada

- **WHEN** abre o carrinho com mensagem comercial não vazia na galeria
- **THEN** lê a mensagem junto às fotos daquela galeria antes de finalizar ou informar pagamento

#### Scenario: Mensagens distintas ou vazias

- **WHEN** o carrinho contém galerias com textos distintos e uma sem mensagem
- **THEN** cada texto aparece somente no seu grupo e a galeria sem mensagem não apresenta bloco vazio

#### Scenario: Texto potencialmente interpretável como HTML

- **WHEN** a mensagem contém marcação HTML
- **THEN** a revisão exibe texto inerte e não executa scripts nem injeta elementos
