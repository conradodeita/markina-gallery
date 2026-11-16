# Spec Delta

## ADDED Requirements

### Requirement: Visibilidade do encerramento do tenant

O console SHALL exibir `Encerrando` e `Encerrado` no diretório e no detalhe do tenant, distinguindo-os de `Ativo` e `Suspenso`. O estado final SHALL informar o instante da conclusão, a origem da transição e há quantos dias a conta está encerrada, sem expor pedidos, clientes, fotos, dados financeiros detalhados ou segredos. Ao completar dez anos, SHALL sinalizar revisão manual da mídia sem apagá-la automaticamente.

#### Scenario: Proprietário consulta tenant encerrado
- **WHEN** `PlatformOwner` autorizado consulta o diretório ou detalhe de um tenant encerrado
- **THEN** vê claramente o estado `Encerrado`, quando e como ocorreu a transição e o contador de dias desde o encerramento

#### Scenario: Conta encerrada há dez anos ou mais
- **WHEN** `PlatformOwner` autorizado consulta uma conta cujo encerramento completou dez anos
- **THEN** o console sinaliza que a revisão manual da mídia está pendente e mantém o contador atualizado, sem expurgar automaticamente a mídia nem bloquear sua recuperação

#### Scenario: Encerramento ainda pendente
- **WHEN** a conta tem solicitação de encerramento, mas ainda há obrigações pendentes ou uma fonte não pôde ser verificada
- **THEN** o console mostra `Encerrando`, sem declarar a conta `Encerrado`

#### Scenario: Usuário sem acesso global
- **WHEN** fotógrafo, cliente ou operador técnico consulta o estado global de encerramento
- **THEN** o backend não revela o status administrativo nem dados de outros tenants

### Requirement: Recuperação da mídia de tenant encerrado

O console SHALL permitir ao `PlatformOwner` solicitar recuperação auditada da mídia por pasta. A conta MUST permanecer fechada até a verificação íntegra das operações solicitadas. Reabrir é ação separada, com senha atual e TOTP; consultar o estado é somente leitura e owner-only. MUST NOT criar link público nem expor credenciais.

#### Scenario: Proprietário solicita recuperação
- **WHEN** o proprietário solicita a recuperação da mídia ainda existente de um tenant encerrado, inclusive após o marco de dez anos
- **THEN** o sistema enfileira a recuperação das pastas arquivadas, informa o estado e registra proprietário solicitante, tenant, UUID idempotente, prazo escolhido, instante, estado por pasta e resultado

#### Scenario: Reabertura após recuperação íntegra
- **WHEN** todas as pastas solicitadas foram restauradas e verificadas integralmente e ainda não se completaram dez anos desde o encerramento
- **THEN** o proprietário pode reabrir o acesso do tenant por ação separada e auditada, preservando o histórico do encerramento e da recuperação

#### Scenario: Reabertura depois da retenção de identidade
- **WHEN** a mídia é recuperada após dez anos desde o encerramento
- **THEN** o console mantém a conta fechada até o CPF fornecido pelo fotógrafo corresponder à impressão protegida do tenant e serem informados dados atuais; depois, o proprietário pode concluir a reabertura auditada sem visualizar o CPF nem sua impressão
