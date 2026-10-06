# Spec Delta

## ADDED Requirements

### Requirement: Reautenticação OTP contextual a uma galeria autorizada

Cliente sem sessão SHALL poder solicitar OTP no contexto de uma galeria identificada internamente, desde que já possua vínculo ativo com ela. O identificador da galeria MUST NOT conceder acesso; o vínculo SHALL ser revalidado antes de enviar/re-enviar OTP e antes de criar a sessão.

#### Scenario: Cliente autorizado retoma pelo link da notificação

- **WHEN** o cliente informa nome e telefone na entrada contextual da galeria e possui vínculo ativo com ela
- **THEN** o sistema envia OTP pelo WhatsApp, cria sessão somente após validar o código e retorna à galeria solicitada

#### Scenario: Telefone sem vínculo ativo solicita reautenticação

- **WHEN** um visitante informa telefone sem vínculo ativo com a galeria indicada
- **THEN** o sistema mantém resposta externa neutra, não envia OTP e não concede sessão ou cadastro por esse contexto

#### Scenario: Vínculo revogado durante o desafio

- **WHEN** o vínculo com a galeria deixa de estar ativo antes do reenvio ou validação do OTP
- **THEN** o sistema não entrega novo código e recusa a sessão contextual sem revelar dados da galeria ou cliente
