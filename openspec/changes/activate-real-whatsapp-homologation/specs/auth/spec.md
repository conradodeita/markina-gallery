## Purpose

Preparar a identidade telefônica brasileira na entrada de cliente antes de solicitar o OTP pelo transporte WhatsApp real.

## MODIFIED Requirements

### Requirement: OTP de cliente por WhatsApp

O sistema SHALL autenticar cliente/responsável mediante nome completo, telefone normalizado em E.164 e OTP de uso único enviado pelo adaptador WhatsApp. Na entrada brasileira, a tela SHALL apresentar `+55` como código de país padrão e SHALL exigir DDD seguido de número móvel com o nono dígito `9`, enviando ao backend exatamente `+55DD9XXXXXXXX`.

#### Scenario: Cliente informa telefone móvel brasileiro

- **WHEN** o cliente digita ou cola DDD e número móvel com onze dígitos nacionais, incluindo `9` imediatamente após o DDD
- **THEN** a tela formata o valor para leitura, mantém `+55` visível e solicita o desafio com o telefone E.164 `+55DD9XXXXXXXX`

#### Scenario: Cliente cola E.164 brasileiro completo

- **WHEN** o cliente cola um número válido iniciado por `+55`
- **THEN** a tela remove o país duplicado do campo nacional, preserva os onze dígitos e envia um único prefixo `+55`

#### Scenario: Telefone brasileiro incompleto ou sem o nono dígito

- **WHEN** o valor não contém exatamente DDD, `9` móvel e oito dígitos restantes
- **THEN** a tela explica o formato esperado e não solicita um desafio OTP

#### Scenario: Cliente solicita código

- **WHEN** o cliente informa dados válidos e solicita entrada
- **THEN** o sistema cria desafio OTP com expiração curta, envia o código pelo WhatsApp e exibe a etapa de validação sem revelar se o telefone está cadastrado

#### Scenario: Cliente valida código

- **WHEN** o cliente informa o OTP correto dentro do prazo
- **THEN** o sistema invalida o desafio, cria sessão com papel `client` e encaminha o cliente conforme suas galerias autorizadas

#### Scenario: OTP inválido, usado ou expirado

- **WHEN** o cliente informa código inválido, já usado ou expirado
- **THEN** o sistema rejeita a autenticação, registra a tentativa, mantém resposta neutra e aplica rate limit
