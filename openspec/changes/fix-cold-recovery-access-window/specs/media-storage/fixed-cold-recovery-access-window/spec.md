## ADDED Requirements

### Requirement: Prazo fixo após recuperar pasta fria

Um novo pedido de recuperação fria pelo fotógrafo SHALL conceder 30 dias a partir da conclusão. A recuperação MUST preservar o prazo de pedidos já aceitos, inclusive em replay idempotente e retentativa, e a janela vigente de elegibilidade ao arquivamento. Cada novo ciclo de recuperação SHALL aplicar sua própria taxa vigente.

#### Scenario: Novo pedido do fotógrafo

- **WHEN** o fotógrafo confirma a taxa da recuperação
- **THEN** o sistema registra 30 dias sem exigir seleção de prazo e inicia a contagem somente quando a pasta volta a ficar disponível

#### Scenario: Pedido existente ou retentativa

- **WHEN** uma solicitação idempotente ou retentativa se refere a um pedido aceito com 7 ou 14 dias
- **THEN** o sistema preserva o prazo contratado e o histórico original

### Requirement: Andamento da recuperação e confirmação do débito

A tela do fotógrafo SHALL exibir uma barra alimentada pelos objetos verificados e estados da operação. O produto MUST NOT prometer tempo de download ou indicar sucesso com base só na transferência. O débito SHALL ocorrer uma única vez após verificação e disponibilização integral, preservando reserva e falha conforme o contrato existente.

#### Scenario: Transferência integral aguardando finalização

- **WHEN** todos os objetos estão disponíveis no staging e a verificação ou disponibilização continua
- **THEN** a tela mostra a etapa de finalização e o prazo e o débito não são confirmados antes da conclusão

#### Scenario: Falha ou resultado incerto

- **WHEN** a recuperação falha ou o resultado permanece incerto
- **THEN** a tela mostra o estado correspondente e não declara conclusão nem débito
