# Proposal

## Why

No ensaio remoto de 08/10/2026, a cliente abriu as fotos da galeria A, mas as miniaturas do próprio pedido sem cobrança ficaram como `Prévia indisponível` em Compras. O backend projeta a rota autenticada `/library/purchases/items/{item_id}/preview`, porém a validação de URLs do componente rejeita esse caminho antes de solicitar a imagem.

## What Changes

- Aceitar no componente de prévia somente o formato adicional de rota interna de item de compra já fornecido pela API.
- Preservar as rotas históricas e operacionais autorizadas, prefixo `/api` único, proteção visual, fallback para erro e recusa de URLs externas, originais e alternativas administrativas.
- Explicitar o contrato de apresentação de prévias de pedidos confirmados e seleções sem cobrança finalizadas, conservando autorização do backend por cliente e conta.
- Acrescentar regressões do normalizador e do card de Compras, incluindo a rota real do pedido canônico finalizado.

## Capabilities

### New Capabilities

### Modified Capabilities

- `media-storage/protected-previews`: explicitar a apresentação no portal das prévias autorizadas dos itens de pedidos confirmados ou seleções sem cobrança finalizadas.

## Impact

Frontend `purchase-preview.tsx`, testes do componente/card e documentação de validação. O endpoint do backend já existe e continua sendo a autoridade de acesso; nenhuma migration, configuração, regeneração de mídia, exclusão ou alteração de permissões prevista.

As capas ausentes em Galerias são um achado independente: as duas galerias A têm `cover_photo_id=null`, e o contrato atual da biblioteca projeta somente capa configurada pronta. Não definir capa automaticamente nesta correção. A orientação neutra aprovada para OTP também pertence a trabalho independente.

Publicação depende de CI/revisão, inventário e autorização específicos. O ensaio A+B permanece aberto: o proprietário informou depois que as três sessões observadas pertenciam ao fotógrafo A; não registrar essas sessões como ensaio remoto de fotógrafos distintos.
