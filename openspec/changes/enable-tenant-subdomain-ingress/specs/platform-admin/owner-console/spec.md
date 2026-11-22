# Spec Delta

## ADDED Requirements

### Requirement: Ativação auditada de hostname validado

O console SHALL permitir somente ao PlatformOwner ativar o hostname reservado após confirmar que revisou os gates e o relatório do ingresso para o tenant/host exibidos. A ação SHALL exigir senha, TOTP, estado esperado, UUID de intenção e SHA-256 do relatório; SHALL auditar o hash e a transição, ser idempotente e não alterar o status da conta ou outro tenant.

#### Scenario: Proprietário ativa hostname validado

- **WHEN** o PlatformOwner confirma que revisou o relatório operacional dos gates e reautentica a intenção para o host reservado correto
- **THEN** o console promove somente esse host a `ready` e registra a referência da validação na auditoria

#### Scenario: Validação ausente ou credenciais inválidas

- **WHEN** falta a confirmação/hash ou senha/TOTP/estado esperado são inválidos
- **THEN** o console recusa a ação sem alterar o host ou o estado da conta

#### Scenario: Replay da ativação

- **WHEN** o PlatformOwner repete a mesma intenção de ativação já concluída
- **THEN** o console retorna o resultado anterior sem consumir outro passo TOTP ou duplicar a auditoria

#### Scenario: Troca de conta durante a confirmação

- **WHEN** o PlatformOwner consulta outra conta enquanto preenche a liberação de um endereço
- **THEN** o console limpa o hash, a atestação e as credenciais preenchidas e exige confirmação para a conta e o hostname agora exibidos
