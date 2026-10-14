## Why

Responsáveis diferentes podem querer comprar fotografias do mesmo evento, mas não podem compartilhar seleção, prazo, carrinho ou histórico. A solução precisa preservar o acervo-fonte administrativo e criar galerias privadas independentes, sem duplicar JPEGs nem expor o evento coletivo.

## What Changes

- Modelar uma galeria privada derivada como pertencente a uma única cliente/responsável, com seleção, favoritos, comentários, pedidos, pagamentos e histórico próprios.
- Permitir que o fotógrafo crie outra galeria privada clonada para um segundo responsável a partir do mesmo acervo-fonte ou resultado aprovado, reutilizando somente referências às fotos e as configurações escolhidas.
- Distinguir no fluxo administrativo a galeria-fonte não listada do vínculo individual da cliente, com busca por nome ou telefone, prazo, bloqueio, reativação e visão individual da seleção.
- Preservar pedidos confirmados e entregas na troca controlada de telefone da mesma cliente, sem transferir propriedade de uma galeria a outra pessoa.
- Exibir para cada cliente o estado de cada foto no seu próprio contexto: nova, visualizada mas não comprada ou já comprada, sem revelar dados de outros compradores.

## Capabilities

### New Capabilities

- `client-access/cloned-private-galleries`: propriedade individual, clonagem privada e isolamento de interações e histórico sobre um acervo-fonte comum.
- `gallery-sales/client-selection-operations`: visão administrativa individual de seleção, compra e exportação dos identificadores das fotos, sem dependência de serviço concorrente.

### Modified Capabilities

- `client-access/derived-galleries`: tornar explícita a relação entre biblioteca da cliente, propriedade exclusiva e estado de fotos já compradas.
- `gallery-sales/operational-gallery-interface`: gerir galerias-fonte não listadas, clientes vinculados e suas galerias privadas derivadas.

## Impact

- Modelos, migration aditiva, autorização, APIs FastAPI, auditoria e testes de isolamento entre responsáveis.
- Telas Next.js backend-driven de lista/ficha de galerias, ficha individual da cliente e biblioteca/galeria da cliente.
- Esta mudança não ativa reconhecimento facial, upload em lote por pasta, preços progressivos, checkout, PIX, mensagens WhatsApp ou entrega; essas capacidades continuam em mudanças próprias.
