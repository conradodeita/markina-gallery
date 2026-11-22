# media-storage/google-drive-connection Specification

## ADDED Requirements

### Requirement: Início do OAuth pela interface do proprietário

A interface administrativa SHALL permitir ao proprietário autenticado iniciar OAuth do Google Drive com reautenticação e escopo mínimo.

#### Scenario: Formulário disponível sem conexão ativa

- **WHEN** o proprietário abre Plataforma e não há conexão Drive ativa
- **THEN** a interface apresenta senha e código TOTP para uma confirmação única
- **AND** envia os valores somente à API same-origin, sem persistir ou registrar os valores no frontend

#### Scenario: Reautenticação aceita

- **WHEN** a API valida sessão, papel do proprietário, origem, rate limit, senha e TOTP
- **THEN** cria uma tentativa OAuth curta com state aleatório de uso único e PKCE S256
- **AND** devolve somente a URL de autorização sem client secret ou verifier
- **AND** a interface valida o host HTTPS, caminho e escopo exato `drive.file` antes do redirecionamento

#### Scenario: Reautenticação ou URL recusada

- **WHEN** a reautenticação falha, existe conexão que impede nova autorização ou a URL não corresponde ao endpoint e escopo permitidos
- **THEN** a conexão não é ativada, os campos sensíveis são apagados e a interface apresenta erro neutro
- **AND** nenhuma URL não confiável é aberta

#### Scenario: Consentimento permanece sob controle humano

- **WHEN** o navegador alcança o consentimento Google
- **THEN** o fluxo aguarda a ação explícita do proprietário
- **AND** nenhuma aprovação, quota, chamada Drive, backup ou acesso a arquivo ocorre automaticamente
