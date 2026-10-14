# Operação do carrinho persistente

## Estados e autoridade

O servidor é a única autoridade. O navegador não usa `localStorage` para reconstruir compras.

- `PhotoSelection` representa o carrinho editável da cliente dentro de uma única Galeria pública/privada.
- `SaleOrder` pendente com `checkout_key` e `frozen_at=NULL` é o rascunho retomável. Clicar em `Prosseguir` cria ou sincroniza esse mesmo pedido, seus itens, preço e PIX, sem consumir a seleção.
- `Informar pagamento` revalida prazo, fotos, preço e PIX; depois congela o pedido com `frozen_at`, cria uma comunicação idempotente e remove somente as seleções incorporadas.
- Pedido congelado pendente aparece como `payment_reported` quando há comunicação em revisão e como `awaiting_payment` quando ainda aguarda comunicação.
- Confirmação administrativa muda o estado para `purchased`. Recusa/correção seguem os contratos administrativos existentes.
- Depois do congelamento, novas seleções formam outro rascunho e, portanto, outro pedido complementar da mesma galeria.

A prioridade por foto é `purchased > payment_reported > awaiting_payment > selected > available`. Galerias diferentes nunca compartilham carrinho, cotação ou pedido.

## Compatibilidade de pedidos legados

A migration `20260910_0053_persistent_client_cart` preenche `frozen_at=created_at` para todos os pedidos preexistentes. Isso preserva como imutável qualquer checkout antigo que já tenha consumido a seleção, inclusive pedido pendente sem comunicação. Não há reconstrução automática de `PhotoSelection`, recálculo de preço ou duplicação de item.

O schema e os payloads são aditivos. Um rollback de aplicação pode manter a coluna e os índices; não se deve executar downgrade nem restaurar banco automaticamente depois que a migration começou.

## Concorrência e idempotência

Seleção, remoção, checkout e comunicação adquirem o mesmo lock por associação cliente+galeria. O rascunho editável possui índice único parcial por cliente+galeria. O checkout sincroniza o pedido sob lock e a comunicação consulta novamente o estado depois do congelamento, evitando dois pedidos ou duas comunicações em uma corrida.

As chaves de checkout e comunicação continuam idempotentes. Repetir `Prosseguir` atualiza o rascunho aberto; repetir `Informar pagamento`, inclusive com outra chave enquanto a comunicação está em revisão, retorna a comunicação existente.

## Expiração e reabertura

A cliente pode consultar carrinho e pedidos depois do vencimento, mas não pode adicionar/remover fotos, recalcular checkout ou informar pagamento. Após aprovação administrativa de reabertura com novo prazo, as mutações voltam a ser autorizadas. O frontend não infere autorização apenas porque ainda possui estado em memória.

## Diagnóstico

1. Consultar `GET /library` e confirmar `selection`, `orders` e a ação principal da galeria correta.
2. Consultar `GET /gallery/{gallery_id}/cart` e confirmar `quantity`, `items` e `draft_order_id`.
3. Consultar `GET /gallery/{gallery_id}/payment-communications` e conferir os pedidos congelados, itens e estados.
4. Se o carrinho e o pedido divergirem antes da comunicação, repetir o checkout para sincronizar o rascunho; nunca editar tabelas manualmente.
5. Se a comunicação já existir, não recriar seleção nem pedido. Usar o fluxo administrativo existente para decidir ou corrigir o pagamento.

## Rollback seguro

Retornar somente a aplicação ao SHA saudável anterior e manter a migration aditiva. Pedidos novos continuam legíveis como pendentes/confirmados pela aplicação anterior; a coluna `frozen_at` é ignorada. Não recriar seleções, descongelar pedidos, apagar itens, restaurar dump ou executar downgrade sem inventário e nova autorização humana explícita.
