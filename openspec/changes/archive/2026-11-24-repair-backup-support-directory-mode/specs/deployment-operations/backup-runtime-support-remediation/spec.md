# Spec Delta

## Purpose

Definir uma operação protegida e restrita para corrigir somente o modo do diretório fixo de cópias anteriores usado pelo suporte do runtime de backup.

## ADDED Requirements

### Requirement: Elegibilidade estrita do diretório de suporte

A operação SHALL aceitar somente o diretório fixo existente quando o inventário atual indicar `directory_invalid` com `target_mode_invalid` como única razão do alvo, mantendo tipo de diretório, owner/grupo root e pai válidos. SHALL NOT corrigir outras divergências.

#### Scenario: Somente o modo do alvo diverge
- **WHEN** o fingerprint aprovado representa o diretório existente com `target_mode_invalid` como única razão e pai válido
- **THEN** a operação revalida esses fatos sob lock e pode ajustar somente o modo do alvo para `0700`
- **AND** nenhum outro path é elegível

#### Scenario: Outra divergência, ausência ou estado incompleto
- **WHEN** o alvo estiver ausente, for link simbólico, não for diretório, tiver owner/grupo divergente, pai inválido ou consulta indisponível
- **THEN** a operação SHALL abortar sem alteração e emitir somente código estático allowlisted

### Requirement: Aprovação vinculada à operação protegida

A mutação SHALL estar disponível somente pela operação fixa `repair-support-backups-mode`, no SHA de `main` com CI verde, após aprovação do ambiente protegido `production` e com fingerprint de suporte atual correspondente à conexão e ao inventário completo.

#### Scenario: Aprovação e fingerprint ainda válidas
- **WHEN** o SHA, CI, conexão, ambiente aprovado e fingerprint correspondem à coleta remota revalidada sob lock
- **THEN** a operação pode iniciar a alteração delimitada

#### Scenario: Fingerprint ou precondição diverge
- **WHEN** a fingerprint está ausente ou difere, ou SHA, CI, host, conexão, container ou estado revalidado diverge
- **THEN** a operação MUST abortar antes de alterar o diretório e sem emitir aprovação reutilizável

#### Scenario: Entrada tenta ampliar a operação
- **WHEN** o dispatch fornece caminho, comando, serviço, owner, group ou modo arbitrário
- **THEN** o workflow SHALL rejeitar a entrada e aceitar somente o identificador fixo da operação e o fingerprint exigido

### Requirement: Alteração preserva conteúdo e limites do host

A operação SHALL alterar somente o modo do diretório fixo para `0700`, preservando owner, group, identidade do alvo e todos os conteúdos existentes. MUST NOT ler, enumerar, criar, substituir, mover ou remover conteúdo.

#### Scenario: Correção concluída
- **WHEN** todas as precondições passam e o modo é ajustado
- **THEN** o resultado sanitizado confirma somente a conclusão da operação
- **AND** nenhum caminho, modo observado, UID/GID, nome, conteúdo ou exceção é exposto
- **AND** refs, executáveis, containers, aplicação, banco, Drive, runtime de backup e serviços/timers permanecem inalterados

### Requirement: Verificação pós-alteração fail-closed

Após a alteração, a operação SHALL verificar pelo mesmo objeto aberto que a identidade e metadados permitidos permanecem válidos e que o estado classificado é `ready`. Se não puder comprovar o resultado, SHALL parar sem retry, limpeza ou nova alteração e emitir somente código estático allowlisted.

#### Scenario: Pós-condição integralmente comprovada
- **WHEN** o mesmo objeto continua no caminho fixo, root:root, como diretório, com modo `0700`, pai válido e demais testemunhas invariantes
- **THEN** a operação SHALL confirmar sucesso sanitizado, sem fingerprint reutilizável ou preparação automática

#### Scenario: Identidade ou pós-condição não pode ser comprovada
- **WHEN** o caminho deixa de apontar ao objeto aberto, qualquer metadado ou testemunha diverge, ou uma verificação falha depois da chamada de alteração
- **THEN** a operação MUST parar sem nova escrita ou limpeza, preservar o estado observado e emitir somente `support_backup_mode_unverified`

### Requirement: Inventário independente após a correção

Uma correção bem-sucedida SHALL terminar sem preparar suporte e sem emitir fingerprint para operação posterior; um novo inventário read-only é obrigatório antes de qualquer preparação.

#### Scenario: Reinventário posterior
- **WHEN** a operação protegida confirma o ajuste
- **THEN** nenhum `prepare-support`, troca de ref/executáveis ou inventário do runtime é iniciado automaticamente
- **AND** qualquer etapa posterior exige despacho separado, CI e fingerprint novos e seus gates próprios
