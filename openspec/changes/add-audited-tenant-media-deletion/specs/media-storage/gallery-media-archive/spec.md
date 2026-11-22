# Spec Delta

## Purpose

Controlar a remoção permanente e auditável de cópias de mídia arquivadas, preservando recuperação, isolamento por tenant e verificação integral até que o proprietário confirme a exclusão.

## ADDED Requirements

### Requirement: Exclusão manual após revisão do encerramento

O sistema SHALL permitir que somente o `PlatformOwner` solicite a exclusão permanente da mídia fria de um tenant atualmente `closed`, após o marco de revisão manual de dez anos e reautenticação. O pedido SHALL exigir confirmação explícita e SHALL NOT apagar registros operacionais, financeiros, aceite ou mídia biométrica.

#### Scenario: Proprietário confirma a exclusão elegível
- **WHEN** o `PlatformOwner` autenticado e reautenticado confirma a exclusão de um tenant encerrado cujo marco de revisão venceu
- **THEN** o sistema registra uma solicitação única e auditada e enfileira a remoção dos objetos de mídia fria daquele tenant

#### Scenario: Conta ainda não elegível ou estado divergente
- **WHEN** a conta não está encerrada, o marco de dez anos ainda não venceu, há operação de mídia pendente ou algum ciclo não está arquivado nem já excluído
- **THEN** o sistema recusa o pedido antes de remover qualquer objeto remoto

### Requirement: Exclusão fria cobre o manifesto completo do tenant

O sistema SHALL excluir todos os objetos binários e manifestos de todos os ciclos arquivados do tenant, inclusive ciclos anteriores de uma pasta recuperada e arquivada novamente. O catálogo técnico e os recibos SHALL permanecer para comprovar o resultado, sem reter conteúdo binário.

#### Scenario: Todos os ciclos estão elegíveis
- **WHEN** o pedido autorizado inclui todos os ciclos arquivados do tenant e cada ciclo possui arquivo concluído com limpeza local verificada
- **THEN** o sistema processa os objetos e manifestos de cada ciclo sem afetar objetos, contas ou registros de outro tenant

#### Scenario: Ciclo verificado sem objetos de mídia
- **WHEN** um ciclo arquivado íntegro contém zero objetos de mídia e um manifesto remoto verificado
- **THEN** o sistema inclui e exclui o manifesto como único objeto do ciclo e só conclui após readback ausente

#### Scenario: Ciclo ausente, incompleto ou local
- **WHEN** não há ciclo de arquivo para a conta ou qualquer ciclo/limpeza local não pode ser comprovado como arquivado e íntegro
- **THEN** o sistema bloqueia o lote inteiro antes do primeiro efeito remoto

### Requirement: Exclusão remota requer verificação e recibo

Cada operação de exclusão SHALL validar a identidade e integridade do objeto esperado, solicitar sua remoção e confirmar por readback que o ID remoto está ausente. O sistema SHALL persistir progresso idempotente por objeto e concluir um ciclo somente após remover e confirmar todos os objetos e seu manifesto.

#### Scenario: Remoção integral de um ciclo
- **WHEN** o storage confirma a ausência de todos os objetos e do manifesto esperados
- **THEN** a operação e o ciclo ficam concluídos como excluídos e o recibo guarda contagem, integridade e instante UTC

#### Scenario: Falha parcial ou resultado incerto
- **WHEN** a remoção ou seu readback falha para qualquer objeto
- **THEN** o ciclo permanece indisponível para recuperação, o lote fica pendente de atenção/reconciliação e o verificador protegido de CPF é preservado

#### Scenario: Outro ciclo já autorizado continua após falha parcial
- **WHEN** um ciclo falha e há outras operações ainda enfileiradas no lote autorizado
- **THEN** o sistema pode concluir as demais operações já autorizadas, não repete automaticamente a operação falha e mantém o lote em atenção/reconciliação até retry explícito do proprietário

### Requirement: Recuperação não reverte exclusão permanente

O sistema MUST NOT permitir pull, recuperação ou reabertura completa de um tenant cujo conjunto de mídia tenha sido permanentemente excluído. Retry de exclusão SHALL depender de nova ação explícita e reautenticada do proprietário; falha ou reconciliação MUST NOT gerar retries automáticos.

#### Scenario: Proprietário tenta recuperar mídia já excluída
- **WHEN** um tenant tem ciclo ou lote de mídia marcado como excluído
- **THEN** o sistema recusa a recuperação e mantém o acesso do tenant encerrado

#### Scenario: Operação incompleta precisa de retry
- **WHEN** o proprietário reautenticado solicita continuar uma exclusão comprovadamente falha ou em reconciliação
- **THEN** o worker retoma a operação idempotente existente e revalida o readback antes de concluir

#### Scenario: Retry concorre com transição do worker
- **WHEN** o proprietário solicita retry enquanto o worker altera o estado de uma operação do mesmo lote
- **THEN** o retry serializa a transição pelo coordenador global e somente reenfileira operações após observar o estado confirmado
