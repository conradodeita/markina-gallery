# Validação e continuidade

Change aprovada pelo proprietário após revisão de `proposal.md`, dois deltas, `design.md` e `tasks.md`. Implementação local na branch `codex/fix-invite-https-and-cart-preview`, criada de `origin/develop` em `0fd74b28fe55fad315dd5c0b85eca3db8a6bf85d`. O commit de planejamento `c397172` não foi enviado ao GitHub; PR #118 é somente o relatório da change anterior e permanece separado. Não houve deploy nesta change.

## Task 1.1 — origem pública compartilhada

Extraída a validação de origem usada em notificações faciais para `backend/app/public_origin.py`, com precedência de `PUBLIC_APP_ORIGIN`, fallback legado válido e HTTP local apenas em `development`/`test`/`local`. `notification_public_origin` conserva sua assinatura e tipo de erro público. Adicionados casos de troca de domínio e fallback local sem configuração.

Validação focada: `python -m pytest tests/test_public_origin.py tests/test_facial_notification_origin.py -q` no diretório `backend`: **93 passed**, 21,58 s, exit 0. O pytest em Windows emitiu um `PermissionError` durante o callback de limpeza de seu diretório temporário global após o resumo; não alterou o resultado dos testes nem arquivos do repositório. Lint e integração ampla ficam para o checkpoint 3.1.

## Task 1.2 — links administrativos de capacidade

`_gallery_capability_link` usa a origem pública validada para a criação da galeria, leitura/emissão e rotação de link público, emissão e rotação de convite individual. As cinco escritas validam a origem antes de alterar capacidades ou estado da galeria. Em ambiente implantado, cabeçalhos `Host` e `X-Forwarded-*` divergentes não determinam o link; uma origem ausente, HTTP ou com caminho devolve 503 genérico antes de criar ou revogar capacidade. A leitura usa a mesma validação. Testes de domínio trocado confirmam que um token existente passa a apontar para a nova origem sem reemissão.

Validação focada: `python -m pytest tests/test_gallery_lifecycle.py -q --tb=short -k 'gallery_capability_links_use_configured_https_origin or gallery_capability_writes_fail_closed_on_bad_origin or gallery_capability_rotation_does_not_revoke_on_bad_origin or admin_manages_opaque_public_links_and_individual_invites'` com `--basetemp` isolado: **6 passed, 55 deselected**, 64,10 s, exit 0. A chave de assinatura usada nos novos testes é sintética e definida somente via `monkeypatch`.

## Task 2.1 — prévia do carrinho

O resolvedor `purchasePreviewUrl` aceita a rota canônica `/public-galleries/{galeria}/photos/{foto}/preview` e as duas rotas protegidas já existentes; mantém exatamente um prefixo `/api`. Rejeita URL externa, original, rota admin, prefixo duplicado, travessia e query/fragmento. `CartPage` já renderiza `PurchasePreview` para cada item; o novo teste de integração da página verifica o `src` da foto canônica. Prévia nula e erro de imagem conservam o estado “Prévia indisponível”.

Validação focada: `npm test -- app/purchase-preview.test.tsx app/library/cart/cart.test.tsx` em `frontend`: **2 arquivos, 31 testes passaram**, 29,83 s, exit 0. Dependências instaladas localmente por `npm ci --no-audit --no-fund` a partir do lockfile; `node_modules` ignorado pelo Git.

## Task 2.2 — autorização da mídia canônica

A rota existente `/public-galleries/{parent_gallery_id}/photos/{photo_id}/preview` continua exigindo sessão cliente, acesso à galeria e `authorized_canonical_photo`, que aplica o público da pasta. O teste existente de pastas canônicas agora confirma 403 sem sessão, 200 para Ana após selecionar foto da pasta restrita, 404 para Cris sem permissão, 403 para cliente bloqueada e 404 após revogar a permissão. Nenhum código de autorização foi alterado.

Validação focada: `python -m pytest tests/test_derived_galleries.py -q --tb=short -k canonical_folder_audience_filters_list_preview_and_selection` com `--basetemp` isolado: **1 passed, 91 deselected**, 15,23 s, exit 0.

## Task 3.1 — checkpoint local

- Backend: `python -m ruff check app/public_origin.py app/facial/notifications.py app/main.py tests/test_public_origin.py tests/test_gallery_lifecycle.py tests/test_derived_galleries.py` passou. `python -m pytest tests/test_public_origin.py tests/test_facial_notification_origin.py tests/test_gallery_lifecycle.py tests/test_derived_galleries.py -q --tb=short -k 'public_origin or notification_origin or gallery_capability or admin_manages_opaque_public_links_and_individual_invites or canonical_folder_audience_filters_list_preview_and_selection'` com `--basetemp` isolado passou: **102 testes, 144 deselected**, 145,91 s. A suíte integral do backend fica para o CI do PR.
- Frontend: `npm run lint` passou com **0 erros, 37 avisos**; `npx tsc --noEmit` passou; `npm test` passou com **50 arquivos, 360 testes**; `npm run build` compilou e gerou as 22 páginas, exit 0.
- OpenSpec: `npx -y @fission-ai/openspec@latest validate fix-secure-gallery-invites-and-cart-previews --type change --strict --no-interactive` passou; `npx -y @fission-ai/openspec@latest validate --strict --all --no-interactive` passou **72/72**. Os avisos informativos de outras changes não bloqueiam esta change.
- Revisão: `git diff --check` passou. O diff contém somente composição de link, validador compartilhado, resolvedor de prévias, testes e evidência OpenSpec. A única chave escrita no código é valor explicitamente sintético de `monkeypatch` no teste. Não houve migration, edição de `.env` ou outra configuração persistida, nem alteração de proxy, DNS, PIX ou autorização de mídia. O job `gitleaks` do CI verificará o histórico no PR. Validação visual autenticada e deploy aguardam as tasks 3.2–3.3.
