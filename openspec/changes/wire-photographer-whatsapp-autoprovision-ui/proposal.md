# Proposal

## Why

A especificação prevê que cada fotógrafo SaaS conecte seu próprio WhatsApp em Configurações. O backend já oferece provisionamento idempotente da instância, mas a tela atual apenas salva o número e segue para o pareamento; numa conta nova, sem credencial por tenant, o pareamento não consegue iniciar.

## What Changes

- Usar a rota protegida de provisionamento na primeira configuração de conta SaaS sem instância própria.
- Manter a edição do número por `PATCH` para canais já provisionados ou legados.
- Preservar telefone digitado e estado não pronto quando o provisionamento falhar; não exibir segredos e não persistir QR/código de pareamento na tela.
- Cobrir o primeiro provisionamento, a edição posterior e a falha com testes locais sintéticos.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `messaging`: detalhar a chamada de provisionamento no primeiro uso de Configurações e a transição segura para pareamento.

## Impact

- Interface em `frontend/app/admin/settings/whatsapp-panel.tsx` e testes do componente.
- Integração autenticada existente `POST /admin/whatsapp/channel/provision`; não requer endpoint ou migration nova.
- Teste de contrato da rota com provider sintético; nenhuma chamada à Evolution real, alteração de segredo, serviço remoto ou produção.
