# Proposal

## Why

A central de Notificações ocupa espaço mostrando todos os formulários simultaneamente. O proprietário solicitou cards inicialmente recolhidos e manutenção conservadora, preservando o sistema funcional.

## What Changes

- Mostrar somente destinatário, título e seta no card recolhido; abrir/recolher pelo cabeçalho com suporte a teclado.
- Preservar todos os campos, prévias, rascunhos, validações e salvamento existentes; alternar visibilidade não chama API.
- Auditar frontend/backend, imports, referências e resíduos; remover somente itens comprovadamente descartáveis, com evidência registrada.
- Executar validações locais, revisar o diff e documentar limitações. Após a manutenção local, o proprietário autorizou concluir commit/push e PR; deploy permanece sujeito ao gate operacional.
- Extensão solicitada pelo proprietário: incluir inventário de higienização no servidor de homologação. Examinar somente metadados de caches/infraestrutura; remover apenas resíduos exclusivos e comprovadamente descartáveis após inventário e plano operacional. Se não houver candidato seguro com benefício, registrar a decisão de preservar.
- Corrigir descarte do push de entrega: a allowlist do service worker não aceita o destino já produzido pelo backend, `/library/purchases#order-UUID`. Relato adicional do proprietário motivou a investigação; WhatsApp segue separado, sem causa operacional presumida.

## Capabilities

### New Capabilities

- `messaging/collapsible-notification-settings`: apresentação recolhível da central existente. Complementa `configurable-push-and-whatsapp-notifications` e `add-order-google-photos-delivery`, sem superseder seus contratos.
- `messaging/order-delivery-push-destination`: compatibilidade segura do service worker com o destino autenticado de entrega já especificado.

### Modified Capabilities

Nenhuma spec consolidada é alterada; a central ainda está especificada nas changes ativas.

## Impact

Página e estilos de Notificações, seus testes e script de validação visual. Auditoria local limitada a correções comprovadas; nenhuma alteração de API, dados, regras de negócio, dependências, segredos ou infraestrutura. Bancos, uploads, volumes, arquivos locais de origem incerta e alterações preexistentes serão preservados. Sync/archive dependem de revisão humana posterior.
