# Spec Delta

## ADDED Requirements

### Requirement: Dois modos de entrada com público de pastas independente

A UI administrativa SHALL oferecer somente `Padrão` e `Somente convite individual`, este como padrão de novas galerias; a API SHALL recusar criar/escolher `collective_protected`. A explicação distingue link/OTP de vínculo prévio, informa o público de pastas e não associa o modo ao processamento facial.

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

Etapa 2 SHALL oferecer pagamento obrigatório marcado por padrão e preservar a cobrança existente. Cobrança exige preços fixos/faixas positivos; sem cobrança, seleção independe de PIX ou preço e a configuração fica preservada. Preço zero legado não muda o modo; finalização paga incompatível exige revisão sem alterar pedidos congelados.

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

Cliente autenticada SHALL poder finalizar seleção autorizada na revisão e prazo vigentes, sem PIX; a operação é idempotente e congela fotos e modo. Compras/ficha mostram `Seleção finalizada`, sem pagamento ou receita. Permite TXT/CSV e entrega com notificações autorizadas; não emite aviso de pagamento. Rascunhos pagos editáveis são descartados sem afetar pedidos comunicados. Retenção sem cobrança começa na finalização, sem alterar pedidos pagos.

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

#### Scenario: Seleção sem cobrança descarta somente rascunhos pagos editáveis

- **WHEN** a cliente finaliza uma seleção sem cobrança enquanto há rascunho pago editável e pedido pago já comunicado ou congelado
- **THEN** a conclusão não envia aviso de pagamento informado/confirmado, descarta apenas o rascunho editável e preserva o pedido comunicado/congelado e o snapshot sem cobrança

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
