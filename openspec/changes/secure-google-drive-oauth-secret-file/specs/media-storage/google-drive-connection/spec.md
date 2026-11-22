# media-storage/google-drive-connection Specification

## ADDED Requirements

### Requirement: Segredo do cliente OAuth fora do metadata do container

A API SHALL obter o cliente OAuth Web de um arquivo dedicado montado somente para leitura. Em produção, ela MUST NOT aceitar client ID, client secret ou redirect URI de variáveis de ambiente.

#### Scenario: Arquivo de cliente ausente ou inseguro

- **WHEN** o arquivo estiver ausente, não for regular, for symlink, tiver permissão diferente de `0400` ou contiver JSON inválido
- **THEN** as operações OAuth falham fechadas com erro genérico
- **AND** a resposta e os logs não revelam conteúdo do arquivo nem detalhes do provedor

#### Scenario: Cliente OAuth válido

- **WHEN** o arquivo contém um cliente Web com ID e segredo válidos e uma única URI HTTPS
- **THEN** o backend usa esses valores somente em memória para o fluxo OAuth
- **AND** a configuração persistida do container não inclui variáveis `GOOGLE_DRIVE_*`

#### Scenario: Variáveis legadas presentes sem arquivo válido

- **WHEN** variáveis `GOOGLE_DRIVE_*` existem mas o arquivo dedicado está ausente ou inválido
- **THEN** o backend não usa as variáveis como fallback e mantém o OAuth indisponível
