# Spec Delta

## ADDED Requirements

### Requirement: Meios de pagamento por emissão

Novos checkouts SHALL oferecer credit_card e pix em um único link single_payment. Cada compra SHALL conservar os meios permitidos no snapshot. Legado SHALL permanecer credit_card sem reemitir links ou prometer PIX retroativo. PIX manual SHALL permanecer independente antes da emissão externa.

#### Scenario: Cliente volta do gateway sem pagar
- **WHEN** existe checkout válido não concluído
- **THEN** o Carrinho mostra as fotos e retoma o mesmo link para os meios permitidos
- **AND** não cria PIX manual alternativo para as mesmas fotos reservadas
- **AND** retorno não confirmado ou consulta temporariamente indisponível encaminha ao Carrinho; confirmação ou exceção financeira encaminha a Compras

### Requirement: Confirmação verificável do meio real

Pagamento por cartão ou PIX InfinitePay SHALL ser confirmado somente após consulta servidor-a-servidor payment_check com tenant/credencial históricos e correspondência de compra/NSU/slug/valor/método permitido. MUST NOT confiar no método informado pelo navegador/webhook. A confirmação SHALL conservar método real e idempotência; callbacks de pedidos reabertos MUST NOT confirmar cancelados.

#### Scenario: PIX aprovado no provedor
- **WHEN** payment_check confirma PIX permitido e todos os vínculos/valores conferem
- **THEN** confirma uma única vez os pedidos e mostra PIX InfinitePay em Compras sem decisão manual do fotógrafo

#### Scenario: PIX em link legado exclusivo de cartão
- **WHEN** um resultado PIX se apresenta para snapshot de cartão exclusivo
- **THEN** abre exceção sem confirmar ou alterar nova compra

### Requirement: Webhook tratado como candidato

A integração SHALL solicitar paid por webhook e validar os identificadores por payment_check antes de aplicar confirmação. Endpoint SHALL limitar schema/tamanho/taxa e ignorar valor/método alegados como prova. Duplicatas SHALL ser seguras; erro transitório SHALL permitir nova entrega sem reemitir checkout.

#### Scenario: Payload forjado ou consulta indisponível
- **WHEN** um chamador alega pagamento sem confirmação autoritativa
- **THEN** nenhum pedido é confirmado nem receita registrada

### Requirement: Carrinho concentra intenção ainda não concluída

Compras SHALL manter PIX manual informado/recusado, pagamentos confirmados/entregas e ocorrências excepcionais de conferência financeira. Pendências externas sem conclusão SHALL ficar no Carrinho com fotos/valor/retomada, sem aparência de pagamento confirmado. Sem retorno inconclusivo SHALL continuar protegido e recuperável pelo fotógrafo.

#### Scenario: PIX manual recusado
- **WHEN** o fotógrafo não localiza um pagamento PIX comunicado
- **THEN** Compras mostra Pagamento não localizado, preservando o histórico

### Requirement: Desistência visual preserva conciliação

A cliente SHALL poder esvaziar uma pendência externa do Carrinho pela própria sessão com revisão atual e auditoria. Essa ação MUST NOT cancelar link remoto, liberar fotos reservadas para duplicação, apagar snapshots/receipts ou alterar estado financeiro. GET SHALL conservar desistência.

#### Scenario: Esvaziar e receber retorno tardio
- **WHEN** a cliente esvazia o Carrinho e depois chega evidência financeira
- **THEN** a ocorrência é processada no histórico correto e permanece visível quando necessária
- **AND** a seleção não é restaurada automaticamente nem uma compra nova alterada

#### Scenario: Outra cliente ou revisão obsoleta
- **WHEN** alguém tenta esvaziar uma pendência alheia ou já confirmada
- **THEN** recusa sem vazar dados ou alterar a compra

### Requirement: Orientação fiel e publicação coordenada

A UI SHALL orientar habilitar cartão e PIX no Checkout Integrado e distinguir o PIX manual. Não afirmar exclusividade de cartão ou exigir PIX global desligado. Ativação real SHALL aguardar publicação autorizada com schema0086/API compatível e revisão; o workflow0084 MUST NOT admitir o conjunto por relaxamento de gates.

#### Scenario: Fotógrafo configura integração
- **WHEN** lê a orientação de preparo
- **THEN** entende que novos links oferecem cartão e PIX e o PIX manual do sistema continua existindo
