# Proposal

## Why

Uma tentativa InfinitePay incerta de R$ 0,05 reaparece no carrinho e oculta PIX/cartão mesmo após selecionar fotos novas. A projeção escolhe a última compra pendente do cliente sem correlacionar suas fotos com a seleção atual. O total congelado antigo é confundido com o total da seleção nova, criando um bloqueio sem saída para itens independentes.

## What Changes

- Correlacionar compra pendente e seleção por tenant, cliente e fotos congeladas.
- Mostrar compras pendentes independentes como acompanhamento, sem bloquear escolhas/total de fotos novas.
- Preservar bloqueio, imutabilidade e reconciliação das fotos já reservadas, sem cancelar/reemitir compras incertas.
- Manter troca PIX/cartão antes de emissão e atualizar o total da seleção atual normalmente.

## Capabilities

### New Capabilities

- `gallery-sales/cart-pending-payment-scope`: separar acompanhamento de compras anteriores da seleção atual.

## Impact

Projeção de carrinho backend e UI/testes do carrinho. Sem migration, autenticação, mudança de preço, pagamento real, liberação de reserva ou alteração do adaptador InfinitePay. O HTTP 422 da compra 11f18369 segue diagnóstico independente; não equivale a ausência de link. Publicação corretiva requer autorização específica; a autorização operacional anterior não libera novos releases ilimitados.
