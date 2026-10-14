## ADDED Requirements

### Requirement: Resultado facial sem botão de rejeição
O portal SHALL apresentar resultados faciais sem botão “Não é esta pessoa”, mantendo seleção explícita, favoritos e navegação existentes, sem alteração automática de resultados.

#### Scenario: Cliente consulta resultados
- **WHEN** a busca retorna fotos
- **THEN** a cliente pode ampliar e selecionar, sem ação de rejeição abaixo da foto

### Requirement: Capas clicáveis e autorizadas
A biblioteca SHALL mostrar capa disponível da galeria e preservar nome, evento e “Ver fotos”. Clicar na capa SHALL abrir o mesmo destino autorizado. Pastas individuais SHALL mostrar prévia da própria pasta, mantendo nome, contagem e navegação. Ausência/falha de imagem SHALL preservar acesso textual; mídia SHALL continuar autenticada e restrita ao vínculo.

#### Scenario: Galerias e pastas disponíveis
- **WHEN** a cliente possui galerias com capa e várias pastas liberadas
- **THEN** identifica cada galeria pela capa e cada pasta por sua prévia, podendo usar a imagem para abrir o respectivo destino

#### Scenario: Acesso bloqueado ou capa ausente
- **WHEN** o acesso está indisponível ou a capa não existe/falha
- **THEN** o card mantém informações e ações autorizadas sem expor fotografia indevida nem criar permissão

### Requirement: Correção de pagamento não localizado
O fotógrafo autenticado SHALL poder corrigir recusa financeira para revisão pendente, como já ocorre com confirmação. A correção SHALL ser auditável, idempotente e silenciosa; SHALL preservar snapshots e exigir escopo integral no PIX agrupado. A confirmação posterior SHALL exigir nova decisão explícita e seguir a mensageria vigente.

#### Scenario: Transferência localizada depois da recusa
- **WHEN** o fotógrafo corrige pagamento não localizado e confirma após nova conferência
- **THEN** a comunicação volta à revisão sem notificação e depois o pagamento fica confirmado com seu histórico preservado

#### Scenario: PIX com múltiplos pedidos
- **WHEN** o fotógrafo corrige a recusa de um PIX único
- **THEN** todos os pedidos envolvidos retornam à revisão atomicamente e o grupo fica comunicado, sem decisão parcial

#### Scenario: Repetição ou estado incompatível
- **WHEN** ocorre repetição da correção, tentativa por cliente ou pedido em estado incompatível
- **THEN** o servidor preserva idempotência, autorização e consistência sem duplicar auditoria financeira ou mensagens
