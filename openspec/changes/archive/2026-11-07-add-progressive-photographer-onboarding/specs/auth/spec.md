# Spec Delta

## MODIFIED Requirements

### Requirement: Autenticação forte do fotógrafo

Fotógrafo ingressado pelo website SHALL entrar com e-mail verificado e senha; TOTP SHALL ser exigido nos logins posteriores somente após ativação voluntária confirmada. O proprietário e contas legadas com TOTP MUST continuar exigindo o segundo fator. Nenhuma sessão SHALL ser emitida se tenant, vínculo ou fatores exigidos estiverem inválidos.

#### Scenario: Senha válida exige TOTP
- **WHEN** proprietário, conta legada com TOTP ou fotógrafo do website com TOTP ativo apresenta senha válida
- **THEN** o sistema exige segundo fator e não cria sessão antes de sua validação

#### Scenario: TOTP válido
- **WHEN** fotógrafo com TOTP ativo conclui segundo fator válido e não reutilizado
- **THEN** recebe sessão vinculada somente ao próprio tenant

#### Scenario: Falha de senha ou TOTP
- **WHEN** senha é inválida ou TOTP exigido é inválido
- **THEN** o sistema rejeita com resposta neutra, rate limit e auditoria sem expor qual fator falhou

#### Scenario: Fotógrafo do website sem TOTP ativo
- **WHEN** fotógrafo do website apresenta senha válida com TOTP ausente e tenant ativo
- **THEN** recebe sessão somente do próprio tenant

## ADDED Requirements

### Requirement: Recuperação progressiva da conta criada pelo website

Redefinição de senha SHALL exigir link curto de uso único enviado ao e-mail verificado. Se TOTP estiver ativo, SHALL exigir adicionalmente TOTP ou código de recuperação válido; sem TOTP, o link é o fator de recuperação. A operação MUST consumir o token uma vez e revogar sessões, com resposta neutra e rate limit. A regra substitui a exigência incondicional de TOTP/código da change anterior.

#### Scenario: Conta exploratória sem TOTP
- **WHEN** fotógrafo confirma link válido e nova senha
- **THEN** a senha muda uma vez, sessões antigas são revogadas e não há login implícito

### Requirement: Ativação voluntária do autenticador

Configurações SHALL orientar o fotógrafo a configurar aplicativo autenticador compatível, com QR Code/chave manual protegidos, confirmação de código e códigos de recuperação. Segredo temporário MUST expirar e não integrar logs, URL ou armazenamento persistente do navegador. A ativação SHALL invalidar sessões anteriores e exigir TOTP nos próximos logins.

#### Scenario: Código não confirmado
- **WHEN** fotógrafo inicia configuração mas não confirma código válido
- **THEN** login por senha continua conforme estado anterior e segredo temporário não vira fator ativo
