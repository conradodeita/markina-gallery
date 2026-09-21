## Why

A cliente pode escolher fotos de várias galerias e pastas para pagar em um único PIX. A interface atual duplica galerias em cards de carrinho e exige finalizar cada galeria separadamente, aumentando os passos e dificultando retomar uma seleção ou consultar compras anteriores.

## What Changes

- Disponibilizar os destinos permanentes `Galerias`, `Carrinho (N)` e `Compras` em todas as telas autenticadas da cliente, inclusive nas galerias acessadas por convite.
- Abrir diretamente `Revise suas fotos e faça o PIX` ao acionar o carrinho, sem uma etapa intermediária de cards com `Revisar carrinho`.
- Reunir fotos selecionadas por galeria, identificando suas pastas, com subtotais e um total geral; mostrar uma única área de PIX, QR Code e `Informar pagamento` ao final.
- Persistir a seleção no servidor e permitir retomá-la após navegar, fechar o navegador ou autenticar novamente com a mesma identidade; manter compras comunicadas e confirmadas em histórico independente.
- Criar um agrupamento financeiro que vincule um único pagamento aos pedidos operacionais de cada galeria. A comunicação, confirmação, recusa e correção do pagamento serão consistentes para todo o grupo, mantendo snapshots, auditoria e compatibilidade com pedidos antigos.
- Preservar regras de preço por galeria, elegibilidade, prazos, prévias protegidas e operação de produção/entrega por pedido. A quantidade global não cria uma faixa de desconto entre galerias.
- Substituir expressamente a restrição de pagamento separado definida em `separate-client-cart-and-purchase-history` e nas decisões equivalentes de `persist-client-cart-and-simplify-client-portal`. A decisão de produto desta proposta, confirmada pela pessoa proprietária em 20/09/2026, é permitir um PIX para várias galerias e pastas.

## Capabilities

### New Capabilities

- `gallery-sales/unified-pix-checkout`: revisão consolidada, agrupamento financeiro, pagamento manual único e transições atômicas entre pedidos de várias galerias da mesma cliente.

### Modified Capabilities

- `client-access/derived-galleries`: retomada persistente e navegação entre galerias, carrinho global e compras agrupadas, sempre com autorização do backend.
- `gallery-sales/client-selection-operations`: vínculo visível entre ficha individual e pagamento agrupado, preservando operação por galeria e imutabilidade comercial.
- `gallery-sales/original-gallery-experience`: navegação permanente mobile-first e revisão direta sem duplicação de cards por galeria.

## Impact

Backend FastAPI/SQLAlchemy, migração aditiva PostgreSQL, projeções de biblioteca/carrinho/compras, checkout e decisões administrativas de pagamento, auditoria e eventos de notificação. Frontend: shell da cliente, biblioteca, galerias privadas e autenticadas por convite, revisão e histórico. Os contratos existentes de pedidos individuais precisam de compatibilidade; pedidos históricos não serão combinados retroativamente.

Esta proposta não cria gateway de pagamento nem confirmação bancária automática, não altera canais de notificação ou infraestrutura e não autoriza deploy. A implementação deverá ser validada localmente e depois em homologação autorizada, sem aguardar continuamente pelo CI quando somente esse resultado estiver pendente.
