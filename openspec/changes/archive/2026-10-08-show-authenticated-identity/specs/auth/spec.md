## ADDED Requirements

### Requirement: Identificação visível da sessão autenticada

O sistema SHALL apresentar nas áreas autenticadas do fotógrafo e da cliente a identidade associada à sessão validada pelo backend, sem aceitar essa identidade do navegador.

#### Scenario: Sessão do fotógrafo

- **WHEN** o fotógrafo abre uma tela autenticada da área administrativa
- **THEN** o cabeçalho apresenta `Logado como: [e-mail da conta autenticada]`

#### Scenario: Sessão da cliente

- **WHEN** a cliente abre uma tela autenticada da biblioteca ou de uma galeria
- **THEN** o cabeçalho apresenta `Logado como: [telefone E.164 ativo e verificado da cliente autenticada]`

#### Scenario: Identidade indisponível

- **WHEN** a consulta autenticada de identidade falha ou não retorna sujeito válido
- **THEN** o sistema não inventa nem reutiliza uma identidade anterior e mantém a área utilizável conforme a autorização existente
