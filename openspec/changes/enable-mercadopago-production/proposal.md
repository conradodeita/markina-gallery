# Proposal

## Why

O piloto Orders foi publicado e aceito em Sandbox, mas o bloqueio global de cobranças reais ainda impede fotógrafos de receber pagamentos por suas próprias contas de produção. O proprietário decidiu ampliar o Mercado Pago para todos os fotógrafos, mantendo cada conta, credencial, pedido e recebimento isolados por tenant e reaproveitando a validação Sandbox já concluída.

## What Changes

- Liberar cobranças com credenciais de produção para fotógrafos que configurem e habilitem individualmente sua própria integração Mercado Pago.
- Manter validação servidor-a-servidor da identidade da conta recebedora, cifragem por tenant e separação de pedidos, notificações e reconciliação.
- Preservar o bloqueio das credenciais de teste ao par tenant/cliente permitido pelo servidor e manter o PIX independente.
- Atualizar a regra operacional que hoje limita o lançamento ao piloto do proprietário; documentar a ativação do gate de produção e seus critérios de verificação.
- Reaproveitar a bateria Sandbox já concluída, sem repeti-la como condição de liberação. A habilitação não fará cobranças de teste nem reais por este executor.

## Capabilities

### New Capabilities

- `gallery-sales/mercadopago-production`: disponibilidade de pagamentos Orders reais por conta de produção configurada pelo fotógrafo responsável.

### Modified Capabilities

- `deployment-operations`: substituir o escopo operacional de piloto exclusivo por uma liberação geral controlada, preservando critérios de ativação, saúde e recuperação.

## Impact

O gate existente `MERCADOPAGO_ALLOW_LIVE_PAYMENTS` permanece fechado por padrão até a ativação operacional. Quando a liberação for aplicada, cada fotógrafo continuará dependendo de conta de produção validada e da opção Mercado Pago habilitada no próprio tenant; credenciais de teste continuarão sujeitas a `MERCADOPAGO_TEST_CUSTOMERS`. Não se prevê alteração de schema nem mistura de credenciais, pagamentos ou preferências com PIX. Mudanças de código só serão propostas se a verificação da implementação existente identificar lacuna para esse comportamento.
