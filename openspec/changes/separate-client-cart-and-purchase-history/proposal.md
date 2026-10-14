## Why

A área da cliente ainda mistura intenção de compra com histórico financeiro: `Ver pedido` leva a uma superfície com carrinho, pedidos sem comunicação, filtros e fotos fora do contexto esperado. A cliente precisa reconhecer imediatamente o que ainda pode editar e pagar, separado do que já comunicou como pagamento.

## What Changes

- **BREAKING**: redefinir a navegação comercial da cliente em duas superfícies exclusivas: `Carrinho` para seleções cujo pagamento ainda não foi comunicado e `Compras` para pedidos com pagamento já comunicado ou confirmado.
- Apresentar um carrinho global da identidade autenticada, agrupando visualmente os carrinhos independentes por Galeria pública, com subtotal e ação de checkout próprios por galeria e total geral apenas informativo.
- Impedir que fotos, preços, prazos, PIX ou pedidos de galerias diferentes sejam combinados em um mesmo checkout ou comunicação de pagamento.
- Mover imediatamente para `Compras` o pedido congelado quando a cliente comunicar o pagamento, removendo-o do carrinho sem depender da confirmação administrativa.
- Substituir rótulos ambíguos como `Ver pedido` por `Ver compra` ou `Compras` quando o destino for o histórico financeiro.
- Simplificar o histórico para mostrar somente compras comunicadas/confirmadas, com galeria, fotos, quantidade, valor, data e estado essencial.
- Remover filtros e demais controles de seleção da superfície de histórico de compras; eles permanecem somente onde forem necessários para montar ou editar um carrinho.
- Preservar carrinhos, pedidos complementares e estados financeiros como registros independentes por cliente e galeria.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/client-selection-operations`: distinguir carrinho editável de compra comunicada e definir agregação visual global sem checkout entre galerias.
- `gallery-sales/original-gallery-experience`: simplificar rótulos, navegação e conteúdo das superfícies `Carrinho` e `Compras`, removendo filtros do histórico.
- `client-access/derived-galleries`: apresentar carrinhos de várias jornadas agrupados por galeria e histórico financeiro separado, sempre orientados pelo backend.

## Impact

- Projeções e endpoints FastAPI usados pela biblioteca, carrinho e histórico, somente se a resposta atual não permitir classificar os registros de forma autoritativa e eficiente.
- Páginas Next.js da biblioteca, carrinho/galeria privada e componentes de cards de pedido, navegação e estados vazios.
- Testes direcionados de isolamento por galeria, transição após comunicação, agrupamento, rótulos, ausência de filtros e responsividade.
- Nenhuma migration prevista; nenhuma alteração em preço, PIX, confirmação administrativa, WhatsApp, mídia, reconhecimento facial, permissões ou dados existentes.
