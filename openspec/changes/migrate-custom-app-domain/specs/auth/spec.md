## ADDED Requirements

### Requirement: Origens confiáveis explícitas durante a migração de domínio

O sistema SHALL validar o cabeçalho `Origin` de operações sensíveis contra a origem HTTPS canônica configurada e origens HTTPS adicionais explicitamente configuradas. Origens adicionais SHALL ser validadas como origens exatas sem credenciais, caminho, query, fragmento ou wildcard. A ausência de `Origin` SHALL preservar o comportamento vigente.

#### Scenario: Operação iniciada no novo domínio

- **WHEN** uma operação sensível é enviada com a origem canônica HTTPS configurada
- **THEN** a verificação de origem aceita a requisição

#### Scenario: Acesso antigo preservado por allowlist

- **WHEN** uma operação sensível é enviada do hostname antigo listado explicitamente nas origens permitidas
- **THEN** a verificação de origem aceita a requisição durante a transição

#### Scenario: Origem externa não configurada

- **WHEN** uma operação sensível é enviada de uma origem ausente da configuração
- **THEN** a API responde com recusa de origem
