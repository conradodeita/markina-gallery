# deployment-operations Specification

## ADDED Requirements

### Requirement: Dependências runtime do frontend corrigidas

O build de produção do frontend SHALL usar o lockfile reproduzível com `npm ci`, e as dependências runtime SHALL permanecer sem vulnerabilidades conhecidas de severidade alta ou crítica apontadas pela auditoria npm.

#### Scenario: Auditoria do conjunto runtime

- **WHEN** a auditoria npm é executada com dependências de desenvolvimento omitidas sobre o lockfile do frontend
- **THEN** o resultado SHALL conter zero vulnerabilidades altas ou críticas nas dependências runtime

#### Scenario: Atualização compatível do Next.js

- **WHEN** uma correção de segurança é aplicada ao frontend
- **THEN** `next` e `eslint-config-next` SHALL permanecer em versões compatíveis da mesma linha principal, e o lockfile SHALL registrar as versões efetivamente instaladas
