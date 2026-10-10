# Validação

## Validação local

A implementação foi portada para `origin/develop` em 10/10/2026. Registrar abaixo apenas evidências executadas nesta base, não reutilizar resultados da branch anterior.

- Backend direcionado: `python -m pytest backend/tests/test_folder_processing.py backend/tests/test_folder_processing_api.py backend/tests/test_facial_engine.py -q` — 16 passaram.
- Suíte completa do backend: em execução; não marcar como concluída até obter o resultado.
- Frontend direcionado: `npm test -- --run app/admin/galleries/folder-processing-panel.test.tsx` — 7 passaram.
- Suíte frontend completa: 57 arquivos e 467 testes passaram; dois testes falharam sob concorrência (timeout de notificações e estado transitório do monitor). Reexecutados isoladamente: notificações 5/5 e monitor 9/9 passaram.
- Ruff: `python -m ruff check backend/app backend/tests` — aprovado.
- ESLint: `npm run lint` — concluído sem erros, com 37 avisos.
- TypeScript: `npm exec tsc -- --noEmit` — aprovado.
- Build: `npm run build` — aprovado.
- OpenSpec estrito: `npx -y @fission-ai/openspec@1.14.0 validate automate-private-folder-processing --strict` — aprovado.
- `git diff --check` — aprovado.
- Migration: não necessária; a change usa a tabela existente `folder_processing_settings`.

## Limitações e gates pendentes

- A revisão visual deve usar a sessão autenticada de fotógrafo fornecida pelo proprietário e dados de homologação autorizados.
- Deploy exige o inventário, subdomínio/portas e plano de impacto zero apresentados conforme `DEPLOY.md`, além do gate de CI/environment `homolog`. Não sincronizar specs principais nem arquivar antes da revisão humana.
