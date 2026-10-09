# Validação

- Backend: os testes `test_parent_gallery_clients_order_by_latest_preview_with_registration_fallback` e `test_parent_gallery_clients_aggregates_commercial_precedence_in_constant_queries` passaram (2 testes). A projeção adiciona uma única consulta em lote e o total permaneceu no limite de 23, independente da quantidade de clientes.
- Frontend: `npm test -- app/admin/galleries/gallery-editor.test.tsx` passou (55 testes), incluindo a ordem recebida e o estado recolhido do menu `Acervo da cliente`.
- TypeScript: `npx tsc --noEmit` passou.
- Ruff: `ruff check app/main.py ../backend/tests/test_derived_galleries.py` passou.
- ESLint direcionado passou sem erros; emitiu 10 avisos em imagens e callbacks existentes nos arquivos verificados.
- OpenSpec: a validação estrita da change passou (1 change, 0 issues) e o mesmo comando pinned pela CI, `npx -y @fission-ai/openspec@1.14.0 validate --strict --all`, passou (86 itens, 0 falhas).
- Diff: `git diff --check` passou.
- O build completo e as suítes completas serão executados pelo CI do PR antes da publicação em homologação.
- CI do PR #152: frontend, OpenSpec e gitleaks passaram. O job backend falhou duas vezes antes de iniciar os testes porque o runner não conseguiu baixar `postgres:17-alpine` do Docker Hub (timeouts e limite de pulls sem autenticação); o job `deploy-homolog` foi pulado. Não há falha de teste de código reportada. Execuções: [37995065664](https://github.com/conradodeita/markina-gallery/actions/runs/37995065664).
