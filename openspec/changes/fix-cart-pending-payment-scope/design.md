# Design

## Context

Base integrada 5446cf4d. `cart_payload` retorna a última compra awaiting_payment/verification_required do cliente em card_payment, independentemente de quais fotos estão selecionadas. O frontend usa esse campo para esconder PIX/cartão e não preparar PIX. `_checkout_material` já recusa qualquer foto congelada em pedido pendente/confirmado; a seleção é removida quando a compra de cartão é preparada. Portanto o bloqueio indiscriminado de fotos novas não acrescenta proteção e impede compras independentes.

## Decisions

Consultar todas as compras de cartão pendentes do tenant/cliente. Comparar os IDs das fotos selecionadas com SaleOrderItem.photo_asset_id_snapshot dos pedidos vinculados à compra, no mesmo owner. Quando não há seleção, manter retomada da compra pendente mais recente. Quando há seleção, card_payment só bloqueia se houver interseção. Projetar as demais em pending_card_payments para acompanhamento separado. Nenhum corpo de provedor/segredo é exposto; não alterar estado, total, snapshots ou reservas.

O frontend prepara PIX para a seleção independente e conserva as duas opções. A área de pendências explicita que o valor pertence a uma compra anterior; não apresenta aumento do valor antigo nem permite pagar novamente suas fotos. O bloqueio imediato após emitir uma tentativa no próprio carrinho permanece até revalidar a seleção. A proteção real de fotos e locks/transações do backend continua obrigatória, inclusive se o cliente ignorar a UI.

## Risks / Trade-offs

Não assumir exclusividade pelo valor ou pela galeria: a correlação é por foto, tenant e cliente; a mesma foto por galerias diferentes continua protegida. Compra incerta permanece sem recuperação automática. HTTP 422 sozinho não encerra tentativa nem comprova valor mínimo. Não criar chamada de teste real para provar ausência de link. Pedidos antigos e reconciliação financeira seguem separados da publicação desta correção.

## Validation

Regressões backend: tentativa unknown, nova foto disjunta com total próprio, PIX preparado somente para nova foto, novo cartão sintético, tentativa antiga imutável, interseção/foto reservada recusada, owner estrangeiro não exposto e várias pendências. Frontend: pendência antiga visível com seletor/total novo, alternância dos meios e bloqueio da tentativa atual. Reutilizar testes existentes, lint/typecheck/build e CI pertinentes. Não alegar pagamento real validado.
