## MODIFIED Requirements

### Requirement: Origens confiáveis explícitas para operações sensíveis
O sistema SHALL validar o cabeçalho `Origin` das operações sensíveis contra a origem HTTPS canônica e origens HTTPS adicionais configuradas explicitamente. Origens adicionais SHALL ser origens HTTPS exatas, sem credenciais, caminho, query, fragmento ou wildcard. A ausência de `Origin` SHALL preservar o comportamento vigente.

#### Scenario: Origem canônica
- **WHEN** uma operação sensível usa a origem HTTPS canônica configurada
- **THEN** a verificação de origem aceita a requisição

#### Scenario: Origem adicional explicitamente permitida
- **WHEN** uma operação sensível usa uma origem HTTPS exata presente na configuração adicional
- **THEN** a verificação de origem aceita a requisição enquanto essa origem permanecer configurada

#### Scenario: Origem ausente ou não configurada
- **WHEN** o cabeçalho `Origin` está ausente ou contém uma origem não configurada
- **THEN** a ausência preserva o comportamento vigente e a origem não configurada é recusada

#### Scenario: Configuração adicional inválida
- **WHEN** a lista de origens adicionais contém credenciais, caminho, query, fragmento ou wildcard
- **THEN** a operação sensível é recusada de forma segura
