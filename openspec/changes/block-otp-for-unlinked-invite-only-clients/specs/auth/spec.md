# Spec Delta

## ADDED Requirements

### Requirement: Elegibilidade contextual antes da entrega de OTP
Quando uma solicitação de OTP usar o link público ou convite individual de uma Galeria pública `invite_only`, o sistema SHALL entregar um código somente se o telefone informado corresponder a uma cliente com vínculo ativo à galeria ou a um convite individual válido destinado à mesma identidade. O sistema SHALL aplicar a mesma regra ao reenvio e SHALL manter respostas neutras que não revelem cadastro, vínculo ou convite.

#### Scenario: Telefone sem vínculo ou convite em galeria `invite_only`
- **WHEN** uma pessoa solicita ou reenvia OTP usando o link público de uma galeria `invite_only` sem vínculo ativo nem convite individual compatível
- **THEN** o sistema não enfileira nem envia OTP e mantém a resposta externa neutra, sem conceder sessão ou acesso

#### Scenario: Cliente vinculada solicita OTP
- **WHEN** uma cliente com vínculo ativo informa o telefone associado ao seu cadastro para uma galeria `invite_only`
- **THEN** o sistema enfileira OTP e permite a validação conforme os limites e a expiração vigentes

#### Scenario: Convite individual compatível
- **WHEN** a solicitação usa convite individual válido e o telefone comprovado corresponde à identidade destinatária
- **THEN** o sistema enfileira OTP para esse telefone, limitado ao escopo do convite

#### Scenario: Cliente é vinculada após uma solicitação sem entrega
- **WHEN** um desafio foi iniciado sem entrega por ausência de vínculo e a cliente passa a ter vínculo ativo antes de solicitar reenvio
- **THEN** o sistema revalida a autorização e pode enfileirar novo OTP somente para a identidade agora vinculada

#### Scenario: Outros contextos de autenticação
- **WHEN** a solicitação ocorre sem contexto de galeria, em galeria `standard` ou em `collective_protected`
- **THEN** o sistema preserva os fluxos autorizados existentes, sem aplicar a restrição específica de `invite_only`

#### Scenario: Link de privada compartilhada
- **WHEN** a solicitação ou reenvio usa um link privado compartilhado válido em vez do link público de uma origem `invite_only`
- **THEN** o sistema preserva a entrega de OTP segundo o contrato de associação privada, sem exigir propriedade individual do link e sem conceder acesso antes da validação

#### Scenario: Privada preservada após exclusão da origem pública
- **WHEN** uma cliente solicita ou reenvia OTP para uma privada habilitada por capacidade válida após a exclusão da origem pública
- **THEN** o sistema preserva a entrega e a autenticação privada autorizadas, sem reabrir a origem pública

#### Scenario: Mesmo telefone em fotógrafos diferentes
- **WHEN** o mesmo telefone possui vínculo ativo ou convite somente com o fotógrafo A e solicita OTP pelo link `invite_only` do fotógrafo B
- **THEN** o sistema consulta apenas a identidade e autorização de B e não entrega OTP por causa do vínculo de A

#### Scenario: Desafio iniciado sem entrega
- **WHEN** a cliente é vinculada depois de um desafio sem entrega e tenta validar um código antes do reenvio autorizado
- **THEN** o desafio não aceita código de seis dígitos nem concede sessão; o reenvio autorizado cria um novo código
