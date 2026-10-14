# Proposal

## Why

Quando o álbum ainda não foi liberado, a cliente vê “Fotos indisponíveis”, mas não sabe onde poderá acessá-lo depois da edição. Um aviso curto deve explicar que o acesso aparecerá em Compras quando o fotógrafo liberar o álbum.

## What Changes

- Exibir, junto ao botão desativado “Fotos indisponíveis”, uma orientação para a cliente acessar o botão “Fotos disponíveis” depois da edição e da liberação do álbum.
- Preservar os estados, o link, as notificações e as regras de pagamento existentes.

## Capabilities

### New Capabilities

- `gallery-sales/order-delivery-access-guidance`: orientar a cliente sobre como acessar o álbum após a edição e a liberação pelo fotógrafo.

### Modified Capabilities

Nenhuma.

## Impact

Alteração de texto em `frontend/app/library/purchase-card.tsx`, cobertura do componente em `frontend/app/library/order-delivery.test.tsx` e atualização da delta spec de entrega. Sem mudanças em API, banco, dependências ou notificações.
