## Purpose

Notificar o fotógrafo de mudanças relevantes nas galerias privadas compartilhadas, com entrega idempotente, auditável e sem expor atividades comerciais entre clientes.

## ADDED Requirements

### Requirement: Notificações administrativas de galeria e membro
O sistema SHALL criar notificação administrativa quando uma galeria privada for criada e quando uma cliente ingressar, for bloqueada ou for desbloqueada. A notificação no painel SHALL ser obrigatória; canais externos configurados SHALL reutilizar o adaptador de mensagens e sua política de retentativa.

#### Scenario: Privada criada pela primeira seleção
- **WHEN** a primeira seleção ou ação administrativa cria uma galeria privada
- **THEN** o fotógrafo recebe uma única notificação `Nova galeria privada criada` com identificadores autorizados e horário

#### Scenario: Nova cliente entra pelo link privado
- **WHEN** um telefone verificado conclui seu primeiro vínculo com a privada
- **THEN** o fotógrafo recebe uma única notificação `Novo cliente na galeria privada` e o evento aparece no histórico administrativo

#### Scenario: Membro bloqueado
- **WHEN** o fotógrafo bloqueia ou desbloqueia uma cliente naquela privada
- **THEN** a mudança produz evento administrativo correspondente sem enviar seleções, valores ou pagamentos a outros membros

### Requirement: Idempotência e privacidade das notificações
Repetição de link, OTP, callback ou job SHALL NOT duplicar a mesma notificação lógica. Conteúdo, logs e erros SHALL limitar dados pessoais ao necessário para o fotógrafo identificar a ação e SHALL NOT incluir segredo do link, OTP ou atividade de outros membros.

#### Scenario: Repetição do vínculo
- **WHEN** a mesma cliente reabre o link e o vínculo já existe
- **THEN** o sistema reutiliza o vínculo sem emitir novamente a notificação de nova entrada

#### Scenario: Falha de canal externo
- **WHEN** uma notificação externa falha de forma retomável
- **THEN** o painel preserva o evento, registra estado sanitizado e permite retentativa conforme a política do adaptador
