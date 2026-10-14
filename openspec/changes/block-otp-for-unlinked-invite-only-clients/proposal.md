# Proposal

## Why

Em galerias configuradas como `invite_only`, foi observado que o primeiro pedido de OTP pode enfileirar uma mensagem antes de o backend confirmar que o telefone pertence a uma cliente vinculada ou a um convite individual válido. A negativa posterior à validação impede o acesso, mas entrega um código desnecessário e confunde a pessoa convidada.

## What Changes

- Fazer o backend decidir a elegibilidade do destinatário antes de enfileirar OTP contextual para galerias `invite_only`.
- No link público de uma galeria `invite_only`, não entregar OTP para telefone sem vínculo ativo com a galeria nem convite individual válido destinado à mesma identidade; preservar respostas neutras e controles contra enumeração.
- Revalidar a elegibilidade no reenvio, permitindo que uma cliente recém-vinculada peça novo código sem reutilizar uma autorização antiga.
- Preservar os fluxos já autorizados: cliente vinculada, convite individual compatível, links privados compartilhados, privadas preservadas após exclusão da origem, cadastro permitido em `standard`, compatibilidade bloqueada do legado `collective_protected`, reautenticação contextual e entrada sem contexto de galeria mediante sessão própria.
- Cobrir com regressões a ausência de entrega para não vinculados, o envio para vinculados/convites válidos e a mudança de elegibilidade entre pedido e reenvio.

## Capabilities

### New Capabilities

### Modified Capabilities

- `auth`: exigir elegibilidade de acesso contextual antes da entrega de OTP e revalidá-la no reenvio, sem revelar a elegibilidade na resposta.

## Impact

- Backend: solicitação e reenvio em `/auth/client/challenge` e `/auth/client/resend`, resolução de vínculo/convite e outbox WhatsApp.
- Testes de autenticação e privacidade de OTP; nenhuma alteração de banco ou configuração externa prevista.
- Frontend deve continuar recebendo resposta neutra e manter um fluxo utilizável após tentativa sem entrega.
