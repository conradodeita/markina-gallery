# Tarefas: restaurar busca financeira na linha de produção

## 1. Reintegração isolada do comportamento aprovado

- [x] 1.1 Comparar o commit `92366f5` com a linha `main` atual e mapear conflitos, mantendo intactas as alterações progressivas da galeria. Evidência: `git merge-tree --write-tree origin/main 92366f5` não indicou conflitos; `origin/develop` está um commit à frente do ancestral comum com `main`.
- [x] 1.2 Reintegrar a API, interface e testes de busca por cliente/telefone, sugestões e filtro fixo pela mesclagem isolada do único commit de `origin/develop`, sem incorporar outras mudanças da linha de desenvolvimento. Evidência: merge local `origin/develop` em `codex/restore-payment-dashboard-search-main`, estratégia `ort`, 11 arquivos alterados, preservando o histórico de `main`.
- [x] 1.3 Confirmar que #177 permanece separado e que nenhum arquivo do workspace local em andamento foi incluído. Evidência: PR #177 continua aberto em `develop`; sua árvore altera manifest/lockfile e OpenSpec de dependências. A branch de restauração parte de `origin/main` e não inclui os arquivos editados no workspace principal.

## 2. Validação

- [x] 2.1 Executar testes backend e frontend direcionados para busca, seleção exata, paginação, resposta sem telefone, sugestões acessíveis e comportamento/posição dos filtros. Evidência: `python -m pytest backend/tests/test_derived_galleries.py -q -k "admin_payment_dashboard_groups_orders_uses_snapshots_and_paginates_without_n_plus_one or admin_payment_dashboard_combines_validated_filters or admin_payment_dashboard_searches_phone_and_exact_client_without_exposing_phone"` — 3 passaram; `npm test -- --run app/admin/payments/page.test.tsx --reporter=dot` — 10 passaram.
- [x] 2.2 Executar lint, typecheck, build aplicável, OpenSpec estrito e `git diff --check`; registrar comandos e resultados. Evidência: `ruff check backend/app/main.py backend/tests/test_derived_galleries.py`, `npx eslint app/admin/payments/page.tsx app/admin/payments/page.test.tsx`, `npx tsc --noEmit`, `npm run build` (23 rotas), `npx --yes @fission-ai/openspec@1.14.0 validate restore-payment-dashboard-search-to-production-lineage --strict` e `git diff --check` passaram. `npm ci` usou o lockfile do `main`; reportou 11 vulnerabilidades já existentes, mantidas no escopo separado do PR #177.
- [x] 2.3 Revisar o diff contra `origin/main`, verificar a preservação do carregamento progressivo e preparar PR para `main`; não fazer merge nem deploy nesta change. Evidência: comparação contém apenas a busca financeira e os artefatos OpenSpec; as rotas/componentes progressivos não têm diff. Branch publicada e PR #181 aberto para `main` (https://github.com/conradodeita/markina-gallery/pull/181). Merge e deploy permanecem fora desta execução.

## Registro de causa

O commit `92366f5` foi integrado em `develop`, mas o release #179 foi construído a partir do `main` que descendia de `aa7119c`. Como o commit da busca não era ancestral de `main`, o release substituiu a interface pela versão sem o filtro. Esta correção reaplica somente o comportamento financeiro aprovado à linha atual de produção.
