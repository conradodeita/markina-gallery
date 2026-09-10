## Purpose

Permitir que uma cliente solicite a reabertura de uma galeria privada expirada e que o fotógrafo decida um novo prazo com visibilidade operacional e auditoria.

## ADDED Requirements

### Requirement: Congelamento após expiração

O sistema SHALL impedir novas seleções, remoções comerciais, checkout e finalização de pedido quando o prazo da galeria privada expirar, preservando consulta a pedidos, compras e entregas existentes.

#### Scenario: Cliente tenta prosseguir após o prazo

- **WHEN** a cliente abre ou retoma uma seleção depois da expiração
- **THEN** a interface explica que a galeria está congelada, não oferece finalização e apresenta `Solicitar reabertura da galeria`

### Requirement: Solicitação idempotente da cliente

O sistema SHALL permitir que qualquer membro ativo de uma galeria privada expirada crie no máximo uma solicitação pendente de reabertura para aquela galeria. A solicitação SHALL ser autenticada, auditada e não reabrirá a galeria automaticamente.

#### Scenario: Primeira solicitação

- **WHEN** a cliente aciona `Solicitar reabertura da galeria`
- **THEN** o backend registra o pedido, mostra `Reabertura solicitada` e enfileira aviso ao fotógrafo quando o canal estiver disponível

#### Scenario: Solicitação repetida

- **WHEN** outro membro ou a mesma cliente solicita novamente enquanto existe pedido pendente
- **THEN** o sistema reutiliza a solicitação existente sem duplicar aviso ou ampliar o prazo

### Requirement: Decisão administrativa por galeria

O sistema SHALL mostrar solicitações de reabertura na área administrativa unificada e nos cards relacionados. O fotógrafo SHALL poder definir uma nova data futura ou recusar a solicitação; a aprovação reabre a galeria inteira para todos os membros ativos.

#### Scenario: Fotógrafo aprova nova data

- **WHEN** o fotógrafo informa uma data futura e confirma a reabertura
- **THEN** o sistema atualiza o prazo da galeria, registra ator e data e permite novamente seleção e checkout a todos os membros ativos

#### Scenario: Fotógrafo recusa a solicitação

- **WHEN** o fotógrafo recusa um pedido pendente
- **THEN** a galeria permanece congelada e a decisão fica visível à cliente sem conceder acesso comercial

### Requirement: Notificação independente da reabertura

O sistema SHALL tratar o aviso WhatsApp ao fotógrafo como efeito assíncrono independente. Falha de mensagem SHALL NOT apagar a solicitação nem impedir sua decisão administrativa.

#### Scenario: Aviso ao fotógrafo falha

- **WHEN** o transporte WhatsApp falha após registrar a solicitação
- **THEN** a solicitação continua visível no painel com estado de entrega e ação de retentativa aplicável

