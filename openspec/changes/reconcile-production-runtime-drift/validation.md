# Validação e evidências

Data da coleta de produção somente leitura: 2026-10-31.

## Base e proveniência

- `origin/main` confirmado por `git ls-remote`: `6af538ecd5c46da7691fa973c33869f263945a25` (PR #351).
- Worktree ativa: `feature/pickyourpic-saas-mainline`, baseada nesse commit.
- Checkout original com alterações preexistentes e worktree anterior baseada em `74f613` foram preservados.
- API: `APP_VERSION=74f61300e7a818d1605afda3db1d07574c443110`, `APP_ENV=production`; endpoints `/api/health` e `/healthz` retornaram HTTP 200.
- Worker: `APP_VERSION=c1944189761799be96eeeb921cad9906484d8b09`, `APP_ENV=production`.
- Comparação dos 144 módulos `app/**/*.py`: API 141/144 iguais a `main`; as três diferenças (`integration_secrets.py`, `facial/crypto.py`, `facial/reference_store.py`) coincidem com os blobs do checkout do servidor em `0dd015a62447e0c8d4c6af16b381140c8118f2ec`. Worker 144/144 coincide com seu `APP_VERSION` e 135/144 com `main`; as nove diferenças são `integration_secrets.py`, `main.py`, `auth.py`, `storage_metrics.py`, `folder_processing.py`, `folder_processing_api.py`, `facial/reference_store.py`, `facial/crypto.py` e `preview_adjustment/api.py`.
- O limite de força de prévia é 75 no runtime worker examinado e 100 em `main`. É um gate de compatibilidade para futura release; não foi observada falha de produção.
- Serviços/versões observados: API Python 3.13.18; worker Python 3.13.17; web Node 24.22.1, Next 16.4.2, React 19.3.1; PostgreSQL 17.11; Redis 7.4.11; Nginx 1.27.5. Versões de dependências adicionais e limites da inspeção estão anotados em `docs/saas-evolution/requirements.json` (R03-009).

## Validação local isolada

- Ambiente Python 3.13.13 dedicado em `C:\codex-data\venvs\pickyourpic-saas-74f613`; Pydantic local 2.14.2 versus 2.14.1 em produção.
- PostgreSQL `17.11-alpine`, efêmero em tmpfs, 1 GiB, 0.5 CPU, 768 MiB, 128 pids e porta publicada apenas em `127.0.0.1:53005`; container exclusivo `pyp-saas-isolated-pg-20261031`.
- `pytest -q backend/tests/test_integration_secrets.py backend/tests/test_facial_crypto.py backend/tests/test_facial_crypto_context.py backend/tests/test_facial_reference_store.py backend/tests/test_app_env_transition.py`: **61 passed**. Sem migrations.
- Suíte adicional `pytest -q backend/tests/test_folder_processing.py backend/tests/test_folder_processing_api.py backend/tests/test_preview_adjustment.py backend/tests/test_storage_metrics.py backend/tests/test_tenant_storage_metrics.py`: **51 passed, 2 skipped, 7 warnings em 183,07 s**. Os skips são reportados pela própria suíte; os warnings são depreciações FastAPI/Starlette, sem falhas.
- `openspec validate reconcile-production-runtime-drift --strict --json`: passou antes da adição deste arquivo; reexecutado após editar os artefatos e passou: ver validação final desta change.

## Limites

Não houve inspeção de registros/fotos de clientes ou conteúdo de pagamentos, escrita em produção, operação financeira, migration, alteração de serviço ou deploy. A auditoria de runtime não demonstra paridade comportamental completa entre as versões e não comprova incidentes. O worker mais antigo exige validação de compatibilidade antes de release.
