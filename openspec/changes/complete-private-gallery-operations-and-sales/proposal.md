## Why

O fluxo administrativo atual mistura acervo público e privado, apresenta contadores comerciais que podem permanecer incorretos e separa Vendas de Pagamentos apesar de ambas tratarem o mesmo pedido. A homologação também revelou que a expiração encerra a seleção sem oferecer à cliente um pedido controlado de reabertura e que a confirmação equivocada não possui correção administrativa auditável.

## What Changes

- **BREAKING**: remover da galeria privada e da etapa Clientes a montagem por fotos já existentes em Galerias públicas ou privadas, incluindo `Adicionar fotos da Galeria pública`, `Adicionar ao acervo privado`, `Carregar novos JPEGs na pública` e o fluxo atual de `Montar galeria privada` com fotos da origem.
- Preservar o fluxo automático existente: quando a cliente seleciona uma foto autorizada na Galeria pública, essa seleção cria ou atualiza sua galeria privada correspondente. A remoção acima alcança somente a montagem manual pelo administrador.
- Permitir que o fotógrafo crie pastas na galeria privada e carregue do próprio dispositivo JPEGs exclusivos daquela privada, processados pelo mesmo pipeline de prévias, proteção e reconhecimento facial, sem torná-los visíveis ou reutilizáveis em outra galeria.
- Corrigir no backend as contagens de fotos no acervo privado, selecionadas e compradas e atualizar as superfícies administrativas quando dados comerciais mudarem; substituir rótulos vagos por `Fotos no acervo privado`, `Fotos selecionadas` e `Fotos compradas`.
- Manter a confirmação de pagamento disponível somente para pedido cujo pagamento foi comunicado pela cliente; a confirmação financeira será persistida independentemente da entrega WhatsApp.
- Permitir correção administrativa auditável de uma confirmação equivocada, retornando o pedido a `Pagamento comunicado — aguardando revisão`, ajustando compras e estatísticas e sem enfileirar mensagem para a cliente.
- Centralizar Vendas e Pagamentos em uma única área por cliente, pedido e Galeria pública, mantendo pedidos de galerias diferentes separados e reunindo seleção sem pedido, aguardando pagamento, pagamento comunicado, confirmado e falha de mensagem.
- Expor nos cards da Galeria pública e privada os estados comerciais reais, a comunicação do pagamento e a ação contextual de confirmação; mostrar prévia do template global de confirmação e atalho de edição com aviso de efeito global.
- Quando o prazo expirar, congelar novas seleções e checkout, preservar histórico e permitir à cliente solicitar reabertura; o pedido aparece no painel e nos cards, notifica o fotógrafo por WhatsApp e permite definir nova data para toda a galeria privada.

## Capabilities

### New Capabilities

- `media-storage/private-gallery-media`: propriedade exclusiva, pastas, upload e processamento de JPEGs enviados diretamente para uma galeria privada.
- `gallery-sales/sales-payment-operations`: painel unificado de vendas e pagamentos, estados por pedido, confirmação condicionada à comunicação e correção administrativa sem mensagem.
- `gallery-sales/gallery-reopening-requests`: solicitação da cliente e decisão administrativa de reabertura da galeria privada expirada.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: remover derivação manual por fotos públicas, corrigir métricas e operar pastas e JPEGs próprios da privada.
- `gallery-sales/client-selection-operations`: separar seleção, pedido e compra por galeria e refletir contadores e estados comerciais autoritativos.
- `client-access/derived-galleries`: bloquear seleção e checkout após expiração, preservar histórico e oferecer solicitação de reabertura.
- `client-access/cloned-private-galleries`: encerrar a criação administrativa de novas privadas por clonagem de referências existentes, preservando somente a leitura e a limpeza segura de dados legados.

## Impact

- Modelos SQLAlchemy, migration Alembic aditiva, lifecycle de mídia privada, agregações e estados de pedidos/comunicações/reabertura.
- APIs FastAPI administrativas e da cliente para uploads privados, métricas, decisão/correção de pagamento e reabertura.
- Worker de mídia, indexação facial e outbox WhatsApp, mantendo falhas de entrega independentes das transições financeiras.
- Páginas administrativas de galerias, Clientes, Vendas/Pagamentos, Configurações e páginas privadas da cliente.
- Testes backend/frontend, migrations, documentação operacional, inventário e validação humana em homologação antes de sincronizar ou arquivar.
