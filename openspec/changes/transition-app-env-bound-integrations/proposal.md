# Proposal

## Why

O inventário read-only de produção confirmou que a API usa um `APP_ENV` conhecido diferente de `production`. O código também vincula esse valor ao AAD das credenciais cifradas por tenant e a configurações de canais, então uma troca direta pode interromper a leitura de credenciais e integrações antes da liberação geral do Mercado Pago.

## What Changes

- Criar inventário somente-leitura, agregado e redigido das configurações e envelopes vinculados ao ambiente, sem expor valores, identificadores de tenants ou material criptográfico.
- Definir uma transição protegida que preserve a identidade e o conteúdo das credenciais cifradas ao mudar o contexto de ambiente, mantendo registros, pedidos, pagamentos, histórico e PIX.
- Validar separadamente as configurações externas de WhatsApp/e-mail e impedir cópia ou reclassificação automática de credenciais entre ambientes.
- Exigir backup verificável, fingerprint exato, aprovação humana, aplicação transacional, recuperação documentada e verificações posteriores. O gate de pagamentos reais permanece fechado durante esta change; nenhum pagamento real será emitido.

## Capabilities

### New Capabilities

- `deployment-operations/app-env-transition`: inventário, migração e recuperação controlados de credenciais e integrações vinculadas ao `APP_ENV`.

### Modified Capabilities

Nenhuma.

## Impact

Afeta o cofre genérico de credenciais cifradas, os registros Mercado Pago por tenant, configurações ambientais de WhatsApp/e-mail, variáveis e serviços Docker Compose, a operação PostgreSQL e os workflows/scripts protegidos de preflight e release. Não altera a lógica do PIX nem os estados ou identificadores financeiros. A execução em produção permanece condicionada a inventário e plano de impacto revisável próprios.
