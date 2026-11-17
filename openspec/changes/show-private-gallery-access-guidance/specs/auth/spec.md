# Spec Delta

## ADDED Requirements

### Requirement: Orientação de acesso a galeria somente por convite

Quando a entrada contextual for de uma galeria `invite_only`, o sistema SHALL mostrar orientação de galeria privada sem exibir inicialmente o campo OTP. A orientação MUST depender somente do contexto da galeria, nunca do vínculo do telefone. A cliente SHALL poder abrir explicitamente a etapa do código.

#### Scenario: Visitante sem vínculo solicita acesso

- **WHEN** uma visitante informa seus dados em contexto `invite_only` sem vínculo ou convite elegível
- **THEN** a interface mostra “Esta galeria é privada. Para acessar, peça ao fotógrafo um convite individual.” sem mostrar o campo de código, e o servidor mantém a resposta neutra e não entrega OTP

#### Scenario: Cliente convidada continua para o código

- **WHEN** uma cliente com acesso permitido solicita autenticação no mesmo contexto `invite_only`
- **THEN** ela recebe a mesma orientação inicial da visitante sem vínculo e pode selecionar “Já tenho um convite” para abrir o campo de código e concluir o OTP

#### Scenario: Orientação não revela vínculo

- **WHEN** dois telefones com elegibilidades diferentes solicitam autenticação no mesmo contexto `invite_only`
- **THEN** ambos recebem o mesmo marcador de orientação e a mesma interface inicial, sem revelar qual telefone possui vínculo ou convite

#### Scenario: Galeria padrão mantém o fluxo atual

- **WHEN** uma cliente solicita OTP no contexto de uma galeria `standard`
- **THEN** a interface mostra a orientação condicional e o campo “Código de acesso” conforme o fluxo atual
