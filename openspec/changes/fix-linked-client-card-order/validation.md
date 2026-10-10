# Validação

- Backend: os testes `test_parent_gallery_clients_order_by_latest_preview_with_registration_fallback` e `test_parent_gallery_clients_aggregates_commercial_precedence_in_constant_queries` passaram (2 testes). A projeção adiciona uma única consulta em lote e o total permaneceu no limite de 23, independente da quantidade de clientes.
- Frontend: `npm test -- app/admin/galleries/gallery-editor.test.tsx` passou (55 testes), incluindo a ordem recebida e o estado recolhido do menu `Acervo da cliente`.
- TypeScript: `npx tsc --noEmit` passou.
- Ruff: `ruff check app/main.py ../backend/tests/test_derived_galleries.py` passou.
- ESLint direcionado passou sem erros; emitiu 10 avisos em imagens e callbacks existentes nos arquivos verificados.
- OpenSpec: a validação estrita da change passou (1 change, 0 issues) e o mesmo comando pinned pela CI, `npx -y @fission-ai/openspec@1.14.0 validate --strict --all`, passou (86 itens, 0 falhas).
- Diff: `git diff --check` passou.
- O build completo e as suítes completas serão executados pelo CI do PR antes da publicação em homologação.
- CI do PR #152: frontend, OpenSpec e gitleaks passaram. A execução inicial do backend falhou ao baixar `postgres:17-alpine` do Docker Hub (timeouts e limite de pulls sem autenticação); o job `deploy-homolog` foi pulado. Execução: [37995065664](https://github.com/conradodeita/markina-gallery/actions/runs/37995065664).
- Nova tentativa em 2026-10-09: o pull do Postgres passou, mas Ruff encontrou uma diretiva `noqa` sem uso em `test_capacity_observability_contracts.py`, fora do código funcional desta change. O teste continua verificando a rejeição de timestamp ingênuo; substituí a construção direta por `datetime.fromisoformat("2026-09-30")`. `ruff check backend/app backend/tests` e o teste específico passaram localmente. Execução: [37995468801](https://github.com/conradodeita/markina-gallery/actions/runs/37995468801). O CI completo será reexecutado após publicar a correção; deploy permanece pendente.
- Após atualizar a branch sobre `develop` (que passou a usar o espelho ECR oficial do Postgres), a suíte CI executou integralmente: 1.288 passaram, 20 foram ignorados e 2 falharam. As falhas eram expectativas antigas: ausência do campo `last_access_at` no teste do fallback por registro e limite de consultas sem contar a nova agregação em lote. Atualizei as expectativas e rodei os dois testes localmente: `2 passed`. Lint completo e CI para a revisão corrigida ainda pendentes. Execução anterior: [38003072462](https://github.com/conradodeita/markina-gallery/actions/runs/38003072462).
