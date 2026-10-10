# Validação

## Validação local

A implementação foi portada para `origin/develop` em 10/10/2026. Registrar abaixo apenas evidências executadas nesta base, não reutilizar resultados da branch anterior.

- Backend direcionado: `python -m pytest backend/tests/test_folder_processing.py backend/tests/test_folder_processing_api.py backend/tests/test_facial_engine.py -q` — 16 passaram.
- Suíte completa do backend: job `backend` do CI no PR #156 — aprovado em 24m36s. A execução local duplicada foi encerrada após esse resultado.
- Frontend direcionado: `npm test -- --run app/admin/galleries/folder-processing-panel.test.tsx` — 7 passaram.
- Suíte frontend completa: job `frontend` do CI no PR #156 — aprovado. Execução local: em 57 arquivos, 467 testes passaram e dois falharam sob concorrência (timeout de notificações e estado transitório do monitor). Reexecutados isoladamente: notificações 5/5 e monitor 9/9 passaram.
- Ruff: `python -m ruff check backend/app backend/tests` — aprovado.
- ESLint: `npm run lint` — concluído sem erros, com 37 avisos.
- TypeScript: `npm exec tsc -- --noEmit` — aprovado.
- Build: `npm run build` — aprovado.
- OpenSpec estrito: `npx -y @fission-ai/openspec@1.14.0 validate automate-private-folder-processing --strict` — aprovado.
- `git diff --check` — aprovado.
- CI completo do PR #156: backend, frontend, OpenSpec estrito e gitleaks aprovados; `deploy-homolog` ignorado porque o PR ainda não foi integrado a `develop`.
- Migration: não necessária; a change usa a tabela existente `folder_processing_settings`.

## Limitações e gates pendentes

- A revisão visual deve usar a sessão autenticada de fotógrafo fornecida pelo proprietário e dados de homologação autorizados.
- Deploy exige o inventário, subdomínio/portas e plano de impacto zero apresentados conforme `DEPLOY.md`, além do gate de CI/environment `homolog`. Não sincronizar specs principais nem arquivar antes da revisão humana.
