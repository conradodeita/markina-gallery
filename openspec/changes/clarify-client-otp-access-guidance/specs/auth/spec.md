# Spec Delta

## ADDED Requirements

### Requirement: Orientação condicional de OTP sem revelar elegibilidade

A interface SHALL apresentar após solicitação ou reenvio de OTP de cliente aceitos a mensagem “O código será enviado somente se este telefone tiver acesso à galeria. Se não receber, confirme seu acesso com o fotógrafo.” e o campo “Código de acesso”. A orientação SHALL ser idêntica independentemente do vínculo e SHALL preservar o contrato de autenticação e as mensagens administrativas.

#### Scenario: Solicitação aceita

- **WHEN** a API aceita a solicitação de código da cliente
- **THEN** a interface exibe a orientação condicional e o campo Código de acesso sem afirmar envio efetivo nem revelar vínculo

#### Scenario: Reenvio aceito

- **WHEN** a API aceita o reenvio no mesmo contexto de galeria
- **THEN** a interface exibe a mesma orientação e mantém o desafio/contexto de autenticação

#### Scenario: Autenticação administrativa

- **WHEN** o fotógrafo recebe desafio TOTP
- **THEN** a interface conserva Código do autenticador e sua orientação própria
