# photographer-credit-wallet Specification

## Purpose

Registrar saldo, reservas, consumo e histórico de créditos de cada fotógrafo em um ledger auditável, com idempotência e integração segura aos uploads.

## Requirements

### Requirement: Gate de onboarding antes de nova reserva de crédito

Além de saldo, revisão financeira e regras existentes, o servidor SHALL exigir requisitos de onboarding e configurações operacionais do tenant SaaS antes de reservar crédito para novo upload. Falha de verificação MUST impedir nova reserva sem consumir saldo; operações já iniciadas SHALL ser reconciliadas conforme seu estado persistido.

#### Scenario: Crédito disponível mas onboarding pendente

- **WHEN** fotógrafo tem saldo e solicita nova reserva sem perfil, aceite, PIX ou WhatsApp exigido
- **THEN** a reserva é recusada sem movimento no ledger
