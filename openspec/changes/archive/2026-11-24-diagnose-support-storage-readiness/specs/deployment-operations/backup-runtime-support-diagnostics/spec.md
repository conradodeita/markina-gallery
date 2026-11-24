# Spec Delta

## Purpose

Descrever razões sanitizadas e somente de leitura para a prontidão dos diretórios fixos usados pelo canal protegido de suporte do runtime de backup.

## ADDED Requirements

### Requirement: Razões estáticas para diretórios fixos de suporte

O inventário SHALL preservar o estado agregado atual e fornecer razões adicionais somente por categorias estáticas allowlisted, sem revelar caminhos, owner/grupo/UID/GID, modos, conteúdo, nomes de arquivos ou exceções.

#### Scenario: Diretório fixo é link simbólico
- **WHEN** o estado agregado é `directory_invalid` porque o alvo é um link simbólico
- **THEN** o campo diagnóstico correspondente informa somente `target_symlink`
- **AND** mantém o estado agregado original sem seguir o link

#### Scenario: Diretório fixo tem tipo ou metadados incompatíveis
- **WHEN** o alvo não é link simbólico e falha uma ou mais verificações de tipo, owner, grupo ou modo
- **THEN** o campo diagnóstico correspondente informa todas as razões aplicáveis dentre `target_type_invalid`, `target_owner_invalid`, `target_group_invalid` e `target_mode_invalid`, em ordem estável
- **AND** mantém o estado agregado original sem expor os valores observados

#### Scenario: Outro estado do diretório fixo
- **WHEN** o estado agregado é `ready`, `creatable`, `parent_invalid` ou `unavailable`
- **THEN** o inventário informa somente a categoria correspondente nos campos `support_backup_directory_diagnostics` e `support_state_directory_diagnostics`
- **AND** falha de leitura retorna `unavailable` sem detalhes da exceção

#### Scenario: Inventário de suporte restaurado
- **WHEN** `restore-support-inventory` coleta o estado dos diretórios fixos
- **THEN** retorna os mesmos estados agregados e categorias sanitizadas de `support-inventory`
- **AND** MUST NOT incluir dados brutos, conteúdo de diretórios ou caminhos

### Requirement: Fingerprint e gates continuam fail-closed

As razões diagnósticas SHALL integrar a fingerprint de suporte, sem substituir os estados agregados usados pelas precondições de preparação ou restauração.

#### Scenario: Mudança na razão observada
- **WHEN** qualquer estado agregado ou razão diagnóstica muda após o inventário aprovado
- **THEN** a fingerprint muda e o valor anterior MUST NOT aprovar uma operação protegida

#### Scenario: Diretório continua inseguro
- **WHEN** qualquer estado agregado permanece diferente de `ready` e `creatable`, mesmo que a razão esteja detalhada
- **THEN** `prepare-support` e `restore-support` abortam antes de buscar candidatos ou gravar, sem reparo, limpeza ou recibo

#### Scenario: Diretórios prontos ou criáveis
- **WHEN** os dois estados agregados são `ready` ou `creatable` e o restante dos gates atuais passa
- **THEN** as precondições existentes permanecem aplicáveis, sem ampliar o escopo de caminhos ou operações permitidos
