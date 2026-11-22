# owner-console Specification

## Purpose

Permitir que o proprietário da plataforma administre e audite tenants e suporte suas contas sem misturar privilégios do monitor técnico.

## Requirements

### Requirement: Revogação assistida do TOTP do fotógrafo

Somente `PlatformOwner` autenticado e reautenticado com segundo fator SHALL revogar TOTP ativo de fotógrafo do website em recuperação assistida. A ação SHALL exigir motivo, registrar ator/tenant/conta/instante UTC, invalidar sessões e códigos de recuperação e notificar o e-mail verificado. A ação MUST NOT revelar segredo, alterar senha, criar sessão ou revogar o próprio TOTP do proprietário ou fator de conta legada.

#### Scenario: Fotógrafo perdeu o autenticador

- **WHEN** proprietário confirma revogação para conta específica com motivo e reautenticação
- **THEN** o fator deixa de ser exigido no próximo login por senha e o fotógrafo recebe aviso

#### Scenario: Acesso indevido ou contexto incerto

- **WHEN** fotógrafo, operador técnico, tenant divergente ou proprietário sem reautenticação tenta revogar
- **THEN** o servidor recusa e preserva fatores e sessões

#### Scenario: Fator mudou durante o atendimento

- **WHEN** proprietário envia confirmação com versão anterior do fator da conta selecionada
- **THEN** a operação é recusada e o fator atual permanece ativo

#### Scenario: Repetição após resposta perdida

- **WHEN** proprietário repete o mesmo identificador, alvo, motivo e versão de uma revogação já concluída
- **THEN** recebe a conclusão anterior sem outro aviso ou alteração do fator atual
