## Why

No fluxo de PIX manual, o fotógrafo precisa saber quando o cliente declara ter pago, revisar a informação e comunicar a decisão sem acompanhar conversas isoladas. O cliente, por sua vez, precisa receber uma confirmação clara e registrada após a decisão do fotógrafo.

## What Changes

- Permitir que o cliente comunique o pagamento de um pedido pendente, sem que essa comunicação confirme automaticamente a transação.
- Notificar o fotógrafo por WhatsApp sobre a comunicação recebida, com trilha de auditoria, idempotência e tratamento de falhas de entrega.
- Permitir que o fotógrafo confirme ou recuse manualmente o pagamento no painel administrativo.
- Permitir que o fotógrafo configure uma mensagem segura de confirmação e que o cliente receba a resposta por WhatsApp após a decisão administrativa.

## Capabilities

### New Capabilities

- `gallery-sales/manual-payment-confirmation`: comunicação de pagamento pelo cliente e decisão manual auditável do fotógrafo.
- `messaging/payment-status-notifications`: notificações transacionais de status do pagamento por WhatsApp, com templates controlados e entrega rastreável.

### Modified Capabilities

<!-- Nenhuma especificação principal existente cobre este fluxo. -->

## Impact

- Backend FastAPI, modelos e migration para comunicação, decisão e tentativas de notificação.
- Painéis de cliente e administrador para o fluxo de pagamento e a configuração de mensagem.
- Adaptador WhatsApp real, fila de entrega, configuração de segredos por ambiente e monitoramento operacional.
- Não inclui conciliação automática, processamento de pagamentos, validação bancária, comprovantes em arquivos nem envio de mensagens de marketing.
