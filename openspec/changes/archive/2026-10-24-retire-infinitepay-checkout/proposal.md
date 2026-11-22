# Proposal

## Why

O proprietário decidiu aposentar a InfinitePay antes de integrar o Mercado Pago. O sistema deve deixar de criar cobranças InfinitePay e remover a configuração, a gestão das chaves e o cofre específico. Existem duas compras concluídas com cartão pela InfinitePay; seu histórico financeiro deve continuar consultável. O PIX manual próprio do Pick-your-Pic permanece independente. O proprietário confirmou que é o único fotógrafo e que todas as demais tentativas foram feitas por ele.

## What Changes

- Retirar da interface, API e fluxo do cliente qualquer configuração ou criação de novo checkout InfinitePay.
- Remover os componentes de integração exclusivos: credenciais/cadastro InfinitePay, resolução de chaves, emissão, retorno, webhook e retomada de checkout.
- Remover por migration as configurações e os segredos InfinitePay armazenados, bem como referências técnicas às credenciais e URLs de checkout.
- Preservar pedidos e registros financeiros InfinitePay, transações, valores, estados confirmados, recibos e correções para consulta histórica; apresentá-los como legado, sem ações que reabram links.
- Preservar integralmente PIX manual, seus dados, snapshots, confirmação e interface.
- Manter pagamentos com cartão indisponíveis até uma change posterior integrar o Mercado Pago Orders API.

## Capabilities

### New Capabilities

- `gallery-sales/infinitepay-retirement`: encerramento do checkout InfinitePay com preservação de histórico financeiro e do PIX manual.

### Modified Capabilities

- `gallery-sales/infinitepay-credit-payments`: capability operacional será aposentada; esta change substitui as tasks ainda pendentes da change `add-infinitepay-credit-payments`.
- `gallery-sales/infinitepay-credentials`: gestão e armazenamento de credenciais serão removidos; os registros financeiros históricos não serão removidos.

## Impact

Afeta as telas de Configurações, Carrinho e Compras; rotas de checkout, retorno e webhook; serviços, modelos e testes exclusivos InfinitePay; migrations; projeções administrativas e documentação. A remoção do armazenamento de credenciais precisa preservar as linhas de `ProviderPayment` e suas relações históricas. Nenhuma alteração será feita no banco remoto ou em segredos de ambiente nesta change.

## Non-goals

Implementar Mercado Pago, habilitar pagamentos com cartão durante a transição, alterar PIX manual, reconciliar compras com o provedor, solicitar reembolso, alterar contas externas ou publicar/deployar a aplicação.

## Review

Direção confirmada pelo proprietário em 22/10/2026: primeiro aposentar e higienizar a InfinitePay; implementar Mercado Pago somente depois. Há somente um fotógrafo (proprietário), duas compras InfinitePay concluídas e as demais tentativas foram realizadas pelo proprietário; não é necessário inventariá-las antes de elaborar esta mudança.
