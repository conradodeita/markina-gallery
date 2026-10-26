## Why

No desktop, os identificadores Orders do Mercado Pago ultrapassam as células dos detalhes de pagamento em Vendas e pagamentos, sobrepondo estados e saindo do card. O defeito foi observado no Chrome pelo proprietário e pelo executor.

## What Changes

- Exibir os fatos do pagamento em uma coluna, com identificadores completos e quebra de linha dentro do card.
- Preservar estados, valores, ações, temas e demais detalhes do pedido.
- Correção local de CSS, sem refatoração adicional ou alteração financeira.

## Capabilities

### New Capabilities
- `payment-detail-containment`: contenção dos detalhes financeiros no card administrativo.

### Modified Capabilities

Nenhuma alteração de contrato financeiro.

## Impact

Somente frontend/app/admin/payments/payments.module.css. Base origin/main 52b9886b; coordenação com o chat responsável por expand-preview-adjustment-strength-range, que edita prévias e migration 0090. Nenhuma publicação concorrente será executada por esta correção.
