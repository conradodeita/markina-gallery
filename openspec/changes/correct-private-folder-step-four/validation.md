# Validação

## Escopo

Correção da apresentação de pastas restritas e do lote de aviso iniciado pelo upload na etapa Imagens. Nenhuma migration, alteração de credenciais ou publicação remota foi executada.

## Evidências

- Frontend: `npm test -- app/admin/galleries/gallery-editor.test.tsx` — 63 testes aprovados.
- TypeScript: `npx tsc --noEmit` — aprovado.
- Frontend lint: `npm run lint` — aprovado, 0 erros e 34 avisos em arquivos da base.
- Frontend build: `npm run build` — compilação, checagem TypeScript e geração de páginas aprovadas.
- Backend: `python -m pytest -q tests/test_folder_processing_api.py tests/test_private_upload_batches.py` — 17 testes aprovados; avisos de depreciação FastAPI e ordem de remoção de tabelas no fixture.
- Backend lint: `python -m ruff check app tests` — aprovado.
- OpenSpec: `openspec validate correct-private-folder-step-four --type change --strict` — válido.
- Preflight API/web: `python scripts/check_prod_app_release_scope.py --base b4f15abd6a71585082758062feba7fcfcc225587 --target d92e1ef7485b00c83ba61e25c56cd98f699489bb` — `app_release_ready=true`, `criterio=somente_api_web`.
- Políticas de release: `python scripts/test_prod_app_release_scope.py`, `python scripts/test_classify_prod_release.py` e `python scripts/test_production_release_workflow_policy.py` — 18 testes aprovados.
- Revisão do diff: `git diff --check` — sem erros; alterações limitadas ao editor, listagem administrativa, testes e artifacts OpenSpec desta change.
- CI da PR #221: frontend, Gemma, gitleaks, política de inventário e OpenSpec passaram; o pytest completo teve 1.692 aprovados e 23 ignorados, mas apontou duas regressões de contrato em pastas públicas porque `client_names: []` havia sido incluído também sem restrição. A resposta foi corrigida para adicionar esse campo apenas a pastas restritas.
- Regressão após correção: `python -m pytest -q tests/test_derived_galleries.py::test_admin_manages_preparing_folders_without_storage_urls tests/test_derived_galleries.py::test_synthetic_gallery_flow_keeps_the_second_folder_administrative tests/test_folder_processing_api.py` — 13 testes aprovados.

## Limitações

Os testes confirmam a criação/fechamento do lote na interface e o processamento/notificação por lote no backend. A correção da regressão identificada pelo CI precisa passar em uma nova execução remota antes do merge. O inventário de produção ocorre no preflight de main; não foi feito envio operacional nem publicado código no servidor nesta change.
