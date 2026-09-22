## Why

O proprietário recebeu em homologação uma notificação facial apontando para `http://localhost:3000`. O deploy sincroniza `PUBLIC_APP_ORIGIN`, mas o worker facial recebe apenas `MARKINA_PUBLIC_URL` com fallback local. Correção solicitada explicitamente após diagnóstico.

## What Changes

- Repassar a origem pública já configurada pelo deploy aos serviços faciais.
- Priorizar `PUBLIC_APP_ORIGIN` ao montar notificações faciais; manter `MARKINA_PUBLIC_URL` somente como compatibilidade quando a origem principal estiver ausente.
- Recusar origem local/privada ou HTTP fora de desenvolvimento/teste, sem enviar mensagem com link incorreto ou cair silenciosamente num fallback.
- Preservar outbox, idempotência, destinatário, permissões e conteúdo da notificação.

## Capabilities

### New Capabilities
- `facial-notification-origin`: resolução e validação da origem dos links faciais.

### Modified Capabilities

Nenhuma alteração às specs consolidadas antes da revisão.

## Impact

Backend de notificações, ambiente compartilhado no Compose e testes. Sem migration, alterações de frontend, envio real de mensagens, edição de `.env` ou deploy nesta etapa. Publicar push + PR e parar para conferência humana do CI conforme preferência vigente.
