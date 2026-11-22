# Spec Delta

## ADDED Requirements

### Requirement: Orientação condicional de OTP sem revelar elegibilidade

Na etapa de validação, a interface SHALL apresentar a mensagem “O código será enviado somente se este telefone tiver acesso à galeria. Se não receber, confirme seu acesso com o fotógrafo.” e o campo “Código de acesso”, sempre igual independentemente do vínculo. Em `invite_only`, essa etapa SHALL ser precedida pelo aviso privado e ação explícita definidos em `show-private-gallery-access-guidance`.

#### Scenario: Etapa de código após solicitação aceita

- **WHEN** a cliente está na etapa de código após a API aceitar sua solicitação e, se o contexto for `invite_only`, após selecionar a ação explícita de continuação
- **THEN** a interface exibe a orientação condicional e o campo Código de acesso sem afirmar envio efetivo nem revelar vínculo

#### Scenario: Reenvio aceito

- **WHEN** a API aceita o reenvio no mesmo contexto de galeria
- **THEN** a interface exibe a mesma orientação e mantém o desafio/contexto de autenticação

#### Scenario: Autenticação administrativa

- **WHEN** o fotógrafo recebe desafio TOTP
- **THEN** a interface conserva Código do autenticador e sua orientação própria
