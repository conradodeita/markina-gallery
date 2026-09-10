## Why

Hoje a seleção persiste até o checkout, mas é removida do carrinho quando um pedido pendente é criado; ao retornar, a cliente não recupera a conferência com fotos, valores e próxima ação, e o portal ainda ocupa espaço com explicações sobre a estrutura interna de galerias. A jornada precisa ser retomável e objetiva para que a cliente reconheça o que selecionou, o que já comunicou e o que comprou.

## What Changes

- **BREAKING**: mover o limite de imutabilidade comercial do clique em `Prosseguir` para a ação `Informar pagamento`; até essa comunicação, o carrinho e o pedido em rascunho permanecem editáveis e sincronizados.
- Persistir no backend um único carrinho/rascunho ativo por cliente e Galeria pública, agregando fotos selecionadas em todas as pastas daquela galeria sem combinar galerias distintas.
- Ao comunicar o pagamento, congelar atomicamente fotos, quantidade, valores, faixas, PIX e regras do pedido; novas escolhas posteriores formam um pedido complementar separado.
- Restaurar, em qualquer novo acesso autenticado, o carrinho, sua revisão, pedidos congelados e os estados por foto: selecionada, pagamento informado e comprada.
- Expor um atalho visível `Carrinho (n)` na jornada da galeria e uma visão curta de pedidos, sempre orientados pelo estado autorizado do backend e utilizáveis entre navegador e celular.
- Simplificar a biblioteca e a galeria da cliente, removendo textos que explicam entidades internas ou repetem regras; manter apenas título, estado essencial e próxima ação.
- Preservar isolamento por cliente, galeria, pedido e sessão OTP, bem como histórico após expiração e os fluxos administrativos já existentes.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/client-selection-operations`: tornar o carrinho retomável, definir o congelamento na comunicação do pagamento e preservar pedidos complementares separados.
- `gallery-sales/original-gallery-experience`: apresentar carrinho e estados comerciais persistidos com textos curtos e ações essenciais no portal da cliente.
- `client-access/derived-galleries`: restaurar carrinho, pedidos e fotos correspondentes em cada jornada autorizada, inclusive após saída ou troca de dispositivo.

## Impact

- Persistência SQLAlchemy/Alembic de estado de rascunho e instante de congelamento em pedidos, com compatibilidade explícita para pedidos pendentes existentes.
- Serviços de checkout, seleção, projeção comercial e comunicação de pagamento no FastAPI, além de payloads da biblioteca, Galeria pública e privada.
- Páginas Next.js de biblioteca, Galeria pública, galeria privada, revisão/PIX e componentes compartilhados de navegação e estado das fotos.
- Testes backend de concorrência, idempotência, isolamento, retomada e snapshots; testes frontend mobile/desktop, acessibilidade, textos e restauração.
- Nenhuma alteração no reconhecimento facial, no acervo autorizado, em mídia, preços, confirmação administrativa ou integrações externas.
