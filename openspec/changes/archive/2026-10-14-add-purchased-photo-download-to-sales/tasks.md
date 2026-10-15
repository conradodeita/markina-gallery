## 1. Contrato e cobertura

- [x] 1.1 Adicionar testes backend para o nome do arquivo com nome Unicode, sanitização de controles/separadores, fallback ASCII e extensão `.html`, preservando o conteúdo autônomo e escaping existente. Evidência: `python -m pytest backend/tests/test_derived_galleries.py -k "confirmed_purchase_download_embeds_preview_without_server_export or purchased_photos_filename_safely_supports_unicode_and_special_characters" -q` — 2 passaram.
- [x] 1.2 Adicionar testes frontend para exibir a ação ao lado de `PaymentActions` somente para pedido confirmado, gerar o URL com cliente e galeria corretos e ocultá-la após correção financeira. Evidência: `npm test -- app/admin/payments/page.test.tsx` — 10 passaram.

## 2. Implementação

- [x] 2.1 Atualizar a resposta HTML do endpoint existente para definir `Content-Disposition` com nome de arquivo seguro contendo o nome da cliente. Evidência: cabeçalho inclui fallback ASCII e `filename*` UTF-8, preserva `.html` e passa nos testes de caracteres especiais.
- [x] 2.2 Adicionar o botão “Baixar fotos compradas” junto às ações financeiras no card confirmado, reutilizando o endpoint existente sem alterar decisões financeiras. Evidência: link usa ID de cliente do grupo e ID da galeria do pedido; fica oculto após correção e quando acervo/galeria foram removidos.

## 3. Validação

- [x] 3.1 Executar os testes backend e frontend direcionados e corrigir regressões causadas por esta change. Evidência na worktree isolada da branch `codex/add-purchased-photo-download-to-sales`: backend direcionado 2 passaram; frontend direcionado 7 passaram; suíte completa frontend 352 passaram em 47 arquivos.
- [x] 3.2 Executar validação OpenSpec estrita e `git diff --check`; registrar comandos, evidências e limitações nesta change. Evidência na worktree isolada: `openspec validate add-purchased-photo-download-to-sales --strict --json` passou; `git diff --check` passou; validação completa das specs registrada em `validation.md`.
