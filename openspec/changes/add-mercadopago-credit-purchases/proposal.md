# Proposal: Compra de créditos via Mercado Pago

## Contexto

A integração Mercado Pago Orders existente permite ao cliente pagar pedidos de fotografias para o tenant/fotógrafo. `MercadoPagoAccount`, `MercadoPagoPayment` e `MercadoPagoWebhook` carregam essa propriedade e a jornada está coberta por testes sintéticos.

A Fase 3 exige que o fotógrafo compre pacote de créditos do proprietário da plataforma. É uma operação financeira diferente: muda pagador, tenant comprador, conta recebedora e consequência de aprovação. O proprietário definiu que o recebimento usará a mesma conta Mercado Pago Orders configurada por ele para as vendas de fotografias. A compra deve reutilizar essa conta e integração sem misturar registros de pedidos de fotos e de carteira.

## Goals

- Criar checkout transparente de compra de pacote dentro da plataforma, com tenant comprador, pacote e preço resolvidos no servidor e snapshot imutável; usar Mercado Pago como único provedor padrão quando a conta existente do proprietário estiver ativa.
- Reutilizar `OrdersProvider`, a configuração protegida e a conta ativa do tenant associado ao proprietário global; resolver conta recebedora no servidor, sem usar a conta do tenant comprador.
- Confirmar saldo somente por evidência autoritativa do backend, exatamente uma vez por compra confirmada.
- Manter pagamentos pendentes/recusados sem saldo disponível; registrar reembolso, estorno e chargeback separadamente e de forma auditável.
- Em reembolso total/parcial ou chargeback confirmado, bloquear novos uploads e compras do tenant até revisão expressa do proprietário; preservar o ledger sem débito automático dos créditos já consumidos.
- Manter operação de compra, referência do ledger e dispatch de confirmação próprios, separados dos pedidos de fotos do cliente; o PIX interno do sistema não será oferecido para compra de créditos.
- Validar primeiro com credenciais e contas de teste do Mercado Pago; não criar pagamentos com credenciais reais sem autorização expressa.

## Non-goals

- Alterar, renomear ou reprocessar compras existentes de fotografias.
- Criar uma segunda implementação independente do protocolo Mercado Pago.
- Definir preços, pacotes ou concessão de saldo inicial.
- Guardar PAN, CVV ou outro dado sensível de cartão.
- Configurar credenciais reais, executar compra financeira real, fazer deploy ou migration remota.

## Evidência inicial

- `MercadoPagoAccount` e seus tokens cifrados pertencem ao tenant recebedor; para pedidos de fotos, esse é o tenant/fotógrafo vendedor. A configuração da conta do proprietário poderá ser reutilizada no checkout de créditos com recebedor e comprador identificados separadamente.
- `mercadopago_checkout.py` contém preparação, submissão, confirmação e reconciliação de Orders API. As rotas e webhooks atuais validam o contexto do recebedor/fotógrafo.
- `MercadoPagoWebhook` exige conta e tenant. A compra de créditos deve resolver a conta do proprietário no servidor e manter a compra vinculada ao fotógrafo comprador sem alterar o ownership dos pedidos de fotos.
- A cobertura existente é sintética; nesta auditoria não houve consulta autenticada de credenciais, notificação real nem transação financeira.

## Decisões humanas e dependências

1. Conta recebedora definida pelo proprietário: usar a conta Orders já configurada no tenant associado a `PlatformOwner`; não criar conta ou credencial global paralela. A separação comprador/recebedor precisa de testes próprios.
2. Aplicar a proteção e rotação de credenciais da conta existente; testar com credenciais e usuários de teste do Mercado Pago quando estiverem disponíveis. A API usa o mesmo host para testes e produção; credenciais reais continuam sujeitas a autorização separada.
3. Decisão aprovada pelo proprietário em 01/11/2026: reembolso total/parcial ou chargeback confirmado bloqueia uploads e novas compras do tenant até revisão do proprietário. O ledger permanece íntegro e não há débito automático pelos créditos consumidos. O proprietário pode liberar o acesso ou manter o bloqueio, com justificativa e evento auditável; uma nova mudança financeira que agrave a situação reabre a revisão.
4. Depende dos contratos da change `add-photographer-credit-wallet`, incluindo pacote ativo, snapshot de preço e evento idempotente de crédito.
5. Mercado Pago é o único provedor padrão da compra de créditos; PIX interno do sistema não participa. PIX ou cartão oferecidos dentro do checkout Mercado Pago continuam sob as regras desse provedor.

## Proteção de compatibilidade

Esta change deve acrescentar um tipo comercial próprio e preservar invariantes/consultas de `MercadoPagoPayment`, `MercadoPagoWebhook`, `SaleOrder`, dashboard de vendas e checkout fotográfico. Reaproveitar somente o transporte/adaptador ou validadores cuja compatibilidade de conta/contexto tenha teste. Uma extensão que altere o sentido das tabelas existentes exige evidência de todos os consumidores e não é presumida nesta proposta.
