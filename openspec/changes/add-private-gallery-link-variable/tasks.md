# Tasks

## 1. Contrato e resolução segura do link

- [x] 1.1 Adicionar `link_galeria` ao contrato de variáveis WhatsApp apenas para `private_photos_ready` e verificar com testes que outros eventos e push a rejeitam. Verificado em `backend/tests/test_notification_settings.py`.
- [x] 1.2 Implementar a resolução do link usando a galeria-mãe persistida e o hostname canônico HTTPS do tenant; verificar caminhos, UUID, esquema e rejeição de host, credencial, porta, query e fragmento não canônicos. Verificado em `backend/tests/test_tenant_hosts.py` e `backend/tests/test_notification_settings.py`.
- [x] 1.3 Integrar a variável ao snapshot do evento e ao tratamento de origem/hostname inválido; verificar que WhatsApp é cancelado antes do transporte e push permanece independente. Verificado no teste de evento de `backend/tests/test_notification_settings.py`.
- [x] 1.4 Incluir a variável e uma prévia representativa na configuração administrativa; verificar API e tela com `backend/tests/test_notification_settings.py` e `frontend/app/admin/notifications/page.test.tsx`.

## 2. Texto padrão e compatibilidade de dados

- [x] 2.1 Criar migração de dados que substitui somente o texto padrão antigo exato pelo novo texto com `{{link_galeria}}` e incrementa a versão; verificado por `backend/tests/test_private_photo_gallery_link_migration.py`.
- [x] 2.2 Verificar com testes que templates personalizados são preservados e que snapshots/outboxes existentes não são alterados nem reenviados; verificado pelo mesmo teste de migração.

## 3. Integração e documentação

- [x] 3.1 Executar testes direcionados do contrato, renderização, segurança de URL, canais e migração; verificado: `python -m pytest tests/test_notification_settings.py tests/test_private_photo_gallery_link_migration.py -q` (13 passaram), conjunto backend integrado (33 passaram), testes de entrega de pedidos (31 passaram) e `npm test -- --run app/admin/notifications/page.test.tsx` (6 passaram).
- [x] 3.2 Validar OpenSpec em modo estrito e checks locais aplicáveis (Ruff, ESLint, TypeScript, build Next.js e head Alembic); revisar `git diff --check` e o diff para confirmar escopo.

## Workflow follow-up

- Revisar a implementação e a evidência com o proprietário antes de sincronizar a spec principal e arquivar a change.
- Executar o CI remoto no fluxo de PR e revisar seu resultado antes de qualquer publicação.
- Qualquer publicação em homologação ou produção segue o gate operacional e a autorização humana aplicáveis.
