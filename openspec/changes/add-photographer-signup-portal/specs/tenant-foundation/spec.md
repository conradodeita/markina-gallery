# Spec Delta

## MODIFIED Requirements

### Requirement: Operação restrita a um fotógrafo nesta etapa

O sistema SHALL manter cadastro público desabilitado até os gates R14 e externos. Após prontidão, o website SHALL ativar automaticamente cada fotógrafo que verificar e-mail e definir senha, sem aprovação manual e sem exigir TOTP ou Termos operacionais para a conta exploratória. Prova local isolada com dados sintéticos pode preceder publicação; MUST preservar tenant legado, papéis e isolamento por contexto inequívoco.

#### Scenario: Conta única válida
- **WHEN** só a conta legada está ativa
- **THEN** seus vínculos e fluxos continuam preservados

#### Scenario: Contexto de instalação inválido
- **WHEN** sessão tem contexto ausente, suspenso ou ambíguo
- **THEN** a aplicação recusa a operação sem selecionar outra conta

#### Scenario: Cadastro automático válido
- **WHEN** fotógrafo verifica e-mail e define senha após os gates aplicáveis
- **THEN** recebe somente tenant finito e vínculo próprios, sem grants globais ou saldo inventado

#### Scenario: Cadastro incompleto
- **WHEN** OTP não foi verificado ou a senha não foi definida
- **THEN** nenhum tenant ativo ou sessão administrativa é criado
