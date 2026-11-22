# Spec Delta

## MODIFIED Requirements

### Requirement: Autenticação forte do fotógrafo

O sistema SHALL autenticar fotógrafo de signup pelo website com e-mail verificado e senha enquanto TOTP estiver desativado. Se o fotógrafo ativar TOTP voluntariamente, o fator SHALL ser exigido em logins posteriores; revogação assistida pelo `PlatformOwner` segue `add-progressive-photographer-onboarding`. `PlatformOwner` e contas legadas MUST manter seus requisitos de autenticação vigentes. O website SHALL ativar o fotógrafo após verificar e-mail e definir senha, sem aprovação manual.

#### Scenario: Senha válida exige TOTP
- **WHEN** `PlatformOwner`, conta legada ou fotógrafo com TOTP ativado apresenta senha válida
- **THEN** o sistema exige TOTP e não cria sessão antes do segundo fator

#### Scenario: TOTP válido
- **WHEN** conta cujo contrato exige TOTP conclui segundo fator válido e não reutilizado
- **THEN** recebe sessão administrativa vinculada somente ao próprio tenant

#### Scenario: Falha de senha ou TOTP
- **WHEN** um fator é inválido
- **THEN** o sistema rejeita com resposta neutra, rate limit e auditoria sem expor qual fator falhou

#### Scenario: Fotógrafo do website sem TOTP ativo
- **WHEN** fotógrafo do website apresenta senha válida com TOTP ausente e tenant ativo
- **THEN** recebe sessão somente do próprio tenant

## ADDED Requirements

### Requirement: Recuperação da conta criada pelo website

Para fotógrafo ativado pelo website, o sistema SHALL permitir solicitar link curto no e-mail verificado e usar TOTP não reutilizado ou código de recuperação de uso único quando TOTP estiver ativado. Se TOTP estiver desativado, o link do e-mail verificado SHALL ser o fator disponível. A solicitação MUST ter resposta neutra e limite de taxa, sem criar sessão. A mudança SHALL consumir token e fatores aplicáveis atomicamente. O fluxo WhatsApp legado SHALL permanecer disponível.

#### Scenario: Link e fatores válidos quando TOTP ativo
- **WHEN** fotógrafo do website recebe o link no e-mail verificado e apresenta TOTP vigente ou código de recuperação válido
- **THEN** a senha é redefinida uma vez, sessões anteriores são revogadas e o próximo login ainda exige o segundo fator

#### Scenario: Solicitação desconhecida ou inelegível
- **WHEN** o endereço não pertence a cadastro ativado pelo website, ou o canal de e-mail não está disponível
- **THEN** nenhuma conta recebe acesso; a resposta pública não revela existência ou origem da identidade

#### Scenario: Falha de configuração ou contexto
- **WHEN** o transporte, a chave, o tenant ou a identidade necessários estão indisponíveis
- **THEN** o sistema falha fechado sem emitir link útil, alterar senha ou criar sessão

#### Scenario: Conta sem TOTP
- **WHEN** fotógrafo com TOTP desativado apresenta link válido no e-mail verificado
- **THEN** pode redefinir a senha sem exigir um fator que nunca ativou e sem criar sessão

#### Scenario: Replay ou fator inválido
- **WHEN** o token ou fator expirou, foi consumido, pertence a outro contexto ou é inválido
- **THEN** senha e sessões permanecem protegidas, sem consumir código de recuperação por tentativa inválida
