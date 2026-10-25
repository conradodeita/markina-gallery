# Spec Delta

## Purpose

Definir recuperação operacional excepcional de seleções reservadas, por decisão expressa do proprietário de prosseguir sem confirmação externa, mantendo a verdade financeira e a rastreabilidade dos registros anteriores.

## ADDED Requirements

### Requirement: Autorização operacional delimitada

A recuperação SHALL aceitar exclusivamente os três UUIDs, valores e tenant constantes desta operação. A autorização SHALL ser registrada como dispensa de confirmação externa pelo titular. O sistema MUST NOT converter essa dispensa em prova de inexistência, cancelamento remoto ou pagamento recebido.

#### Scenario: Operação autorizada
- **WHEN** o executor recupera as três tentativas autorizadas pelo titular
- **THEN** registra ator, referência da decisão, estados anteriores e resultado local
- **AND** não consulta, cancela ou emite checkout externo

#### Scenario: Escopo ou ownership divergente
- **WHEN** um alvo, administrador, valor ou tenant diverge do inventário autorizado
- **THEN** recusa toda a operação sem gravar recuperação parcial

### Requirement: Recuperação preserva o histórico

A operação SHALL conservar compras, tentativas, URLs, itens e valores congelados. As compras antigas SHALL permanecer em exception e seus pedidos locais em cancelled, com as fotos restauradas à seleção sem duplicações. MUST NOT usar failed_before_issue para uma criação não comprovadamente inexistente.

#### Scenario: Compra aceita ou incerta é recuperada
- **WHEN** os alvos ainda são pendentes, sem confirmação financeira local
- **THEN** os pedidos antigos conservam suas associações e snapshots
- **AND** as fotos voltam ao carrinho sem remover seleções novas

#### Scenario: Cliente retoma por PIX
- **WHEN** a recuperação conclui e o PIX próprio do tenant está disponível
- **THEN** o Carrinho oferece o rascunho PIX válido para a seleção elegível
- **AND** cartão continua dependendo da configuração própria e de decisão posterior da cliente

### Requirement: Proteção transacional e idempotência

A recuperação SHALL serializar com pagamentos e preparações existentes, ser atômica e possuir simulação com rollback. Aplicação SHALL exigir impressão digital da pré-imagem validada. Repetição da mesma operação MUST NOT restaurar novamente fotos que a cliente já reservou em outra compra.

#### Scenario: Pagamento ou carrinho muda após simulação
- **WHEN** o estado, revisão, recibo ou seleção diverge da pré-imagem
- **THEN** recusa a aplicação inteira e requer nova simulação

#### Scenario: Reexecução após nova compra
- **WHEN** a mesma operação já foi auditada e a cliente já iniciou outro pagamento
- **THEN** retorna execução anterior sem recriar seleção nem alterar o novo pagamento

### Requirement: Recusa de fundos confirmados e seleção inelegível

A operação MUST NOT recuperar compra confirmada, com NSU persistido ou recibo verificado, nem habilitar seleção inelegível. O PIX SHALL ser validado pelos contratos existentes antes do commit; qualquer falha SHALL reverter todas as mudanças do lote.

#### Scenario: Confirmação concorrente vence
- **WHEN** uma confirmação autoritativa é gravada antes da recuperação
- **THEN** o lote é recusado e a compra confirmada permanece intacta

#### Scenario: Falha de elegibilidade ou PIX
- **WHEN** alguma foto não aparece na revisão autorizada ou o PIX não corresponde ao total
- **THEN** nenhum alvo é liberado e nenhuma auditoria de recuperação é persistida

### Requirement: Retorno tardio mantém conferência

Um retorno de cartão das compras antigas SHALL continuar sujeito à consulta autoritativa e ao estado exception. MUST NOT confirmar automaticamente os pedidos cancelados nem modificar o PIX novo. A evidência tardia SHALL permanecer retida e auditada para conciliação.

#### Scenario: Cartão antigo retorna depois da recuperação
- **WHEN** chega evidência de pagamento de um checkout antigo recuperado
- **THEN** conserva a exceção e seus recibos sem liberar entrega ou alterar o novo rascunho
- **AND** não afirma que o provedor impediu a cobrança
