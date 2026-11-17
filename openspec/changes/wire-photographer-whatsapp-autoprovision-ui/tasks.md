# Tasks

## 1. Integração da tela de Configurações

- [x] 1.1 Selecionar `POST /api/admin/whatsapp/channel/provision` quando o estado retornado indicar `provider: unavailable`, mantendo `PATCH` para canal existente; validar payload e só liberar pareamento após confirmação válida do servidor. `whatsapp-panel.test.tsx`: 13 testes passaram, incluindo POST confirmado e rejeição de resposta inválida.
- [x] 1.2 Cobrir no teste do componente primeiro provisionamento, edição de canal existente e falha do POST; verificar que a falha conserva o telefone, não mostra canal pronto e mantém o pareamento bloqueado. `whatsapp-panel.test.tsx`: 13 testes passaram.

## 2. Contrato seguro do provisionamento

- [x] 2.1 Adicionar teste local sintético da rota que demonstre o gate de cadastro SaaS ativo e o provisionamento idempotente com provider substituto; verificar negação fora do gate e ausência de chamadas de rede real. `test_admin_security.py`: 27 testes passaram; os dois casos de provisionamento usaram banco SQLite descartável e bloquearam qualquer requisição real ao provider.
- [x] 2.2 Revisar apenas a área diretamente afetada conforme `docs/CONTINUOUS-REFACTORING.md` e validar a change com OpenSpec estrito, testes direcionados, lint/typecheck aplicáveis e `git diff --check`; registrar evidências e qualquer bloqueio restante. OpenSpec estrito, ESLint, TypeScript, build Next, Ruff, testes de UI/backend e `git diff --check` passaram; evidências em `validation.md`.

## Workflow follow-up

- Sincronizar a spec principal e arquivar a change somente após revisão humana.
