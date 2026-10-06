# Validation

## Implementação local — 06/10/2026

- Notificação: o link agora abre `/?reauth=client&return_to=/public-galleries/{uuid}`; não carrega token de convite nem resultado facial.
- Sessão ausente: a tela de entrada exibe nome/WhatsApp; o desafio envia `parent_gallery_id` somente para caminho de galeria UUID estrito. A API só emite OTP quando encontra cliente existente com registro ativo e galeria navegável; telefone não vinculado recebe a mesma resposta neutra, sem desafio persistido ou entrega.
- Reenvio e verificação repetem a checagem de vínculo; a revogação durante o desafio bloqueia o reenvio/verificação. Depois do OTP, o destino é a galeria e o painel facial existente carrega o resultado mais recente escopado à sessão.
- Sessão já válida: a entrada direciona ao retorno interno; as APIs de galeria permanecem autoridade para a autorização.
- Nenhuma migration, capability, convite existente, configuração, mensagem real ou sessão da homologação foi alterada. Não foi executado login/OTP remoto nem deploy.

## Evidência

- Backend focalizado `tests/test_tenant_client_auth.py` e `tests/test_facial_notification_origin.py`: execução ampla terminou com 117 aprovados e uma falha por import ausente de `urlencode`; após a correção, os dois casos parametrizados de envio da mensagem passaram. Total único: **118 casos aprovados**.
- Frontend focalizado `app/session-boundary.test.tsx`, `app/auth-entry.test.tsx`, `app/public-galleries/facial-search-panel.test.tsx` e `app/public-galleries/public-gallery.test.tsx`: **80 testes passaram**; cobre retorno seguro, sessão expirada e válida, solicitação contextual sem capability, redirecionamento após OTP e apresentação do resultado na galeria.
- Ruff nos arquivos backend alterados: passou.
- `npm run lint`: passou sem erros; reportou 37 avisos (principalmente `<img>` e variáveis não usadas) em arquivos existentes do frontend.
- `npm run build`: passou, inclusive TypeScript e geração das 22 páginas estáticas.
- OpenSpec `validate reauthenticate-client-from-facial-notifications --type change --strict --no-interactive`: passou.
- Specs principais sincronizadas em `openspec/specs/auth/spec.md` e `openspec/specs/privacy-biometric/facial-search-notifications/spec.md`; `openspec validate --specs`: **17 passaram, 0 falharam**. A validação reporta avisos de requisitos longos, incluindo requisitos em specs preexistentes.
- `git diff --check`: passou sem erros; Git emitiu avisos de conversão LF/CRLF.

Validação somente local. CI, merge, deploy, OTP/WhatsApp remoto, sync da spec principal e archive continuam fora desta execução.
