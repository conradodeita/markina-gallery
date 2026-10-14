## Why

O fluxo atual possui galerias privadas e objetos de pedido, mas não possui o contrato que permite à cliente selecionar fotos, entender o preço por faixa, finalizar um checkout ou gerar um pedido pendente de PIX. Essa lacuna bloqueia a confirmação manual e as notificações de pagamento já planejadas.

## What Changes

- Adicionar seleção persistente por cliente e galeria derivada, com carrinho e remoção explícita de fotos.
- Adicionar regras de preço por faixa, simulador administrativo e cálculo de total em centavos inteiros.
- Adicionar checkout autenticado que congela fotos, regra de preço, valores e texto comercial em um pedido.
- Adicionar estado pendente de PIX manual e informações de pagamento configuradas pelo fotógrafo, sem conciliação automática, comprovantes ou integração bancária.
- Garantir que fotos confirmadas não possam ser recompradas pela mesma cliente, mas permaneçam vendáveis a outras responsáveis autorizadas.

## Capabilities

### New Capabilities

- `gallery-sales/manual-pix-checkout`: seleção privada, preço por faixas, checkout congelado e PIX manual para pedidos de galerias derivadas.

### Modified Capabilities

<!-- Nenhuma especificação consolidada existente descreve o fluxo de checkout manual. -->

## Impact

- Backend FastAPI, modelos SQLAlchemy e migration aditiva para seleção, regras de preço, pedidos e estados de pagamento.
- Portal da cliente para favoritos/carrinho/checkout e painel do fotógrafo para regras de preço e acompanhamento de pedidos pendentes.
- Testes de autorização, cálculo monetário, imutabilidade e prevenção de recompra pela mesma cliente.
- Esta change cria o pedido pendente consumido posteriormente por `add-payment-confirmation-notifications`; não ativa provedor de pagamento nem exige credenciais externas.
