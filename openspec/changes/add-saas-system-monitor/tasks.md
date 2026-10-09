# Tasks

## 1. Contratos e persistência
- [x] 1.1 Criar modelos, migration aditiva, configuração, proprietário por UUID e permissões; validar contratos, negação e migration sem executar servidor ou migration real; documentar configuração. Evidência: oito tabelas compiladas offline e testes de troca de e-mail/negação (`validation.md`).
## 2. Instrumentação
- [x] 2.1 Implementar buffers HTTP/pool/workers, persistência atômica e coleta limitada; testar agregação, histogramas, falhas, retenção e sanitização sem servidor; documentar escopos. Evidência: testes ORM/funções e regressões do coletor (`validation.md`).
## 3. Árvore e atividade
- [x] 3.1 Implementar árvore, busca, paginação, filtros e sinal autenticado; testar isolamento e estados/expiração/revogação/frequência sem servidor; documentar regras. Evidência: testes SQL e Vitest de expansão, paginação e visibilidade (`validation.md`).
## 4. Host e incidentes
- [x] 4.1 Implementar adaptador e coletor opcional de host; verificar contrato com fixtures e investigar fontes existentes somente leitura; registrar configuração ausente. Evidência: fixtures de procfs/JSON e inspeção SSH somente leitura (`validation.md`).
- [x] 4.2 Implementar incidentes deduplicados e exportação limitada; testar duração, recuperação, permissão e ausência de dados sensíveis; documentar limiares. Evidência: testes de transições, sanitização, limites e revogação durante exportação (`validation.md`).
## 5. Interface
- [x] 5.1 Implementar página, navegação autorizada, histórico, árvore seletiva, exportação e card preservado; executar Vitest, lint/typecheck/build sem subir servidor; documentar acesso. Evidência: 62 testes frontend e build/lint/TypeScript aprovados (`validation.md`).
## 6. Integração
- [x] 6.1 Revisar segurança/diff, executar regressões unitárias permitidas e OpenSpec; registrar evidências e limites sem tocar na campanha. Evidência: 93 testes backend e 62 frontend aprovados, lint/build/OpenSpec válidos; skip PostgreSQL e falha adicional de concorrência SQLite delimitados em `validation.md`, com validação remota pendente em 6.2.
- [ ] 6.2 Validar migration/integração PostgreSQL e jornadas no ambiente remoto após autorização de publicação/configuração e concessão das novas permissões; sem carga ou alteração A+B.

Estado de 6.2 em 09/10/2026: proprietário autorizou migration, deploy, configuração, indicação inicial do proprietário/grants e validação remota. Código ainda não publicado; preparar PR exclusivo do monitor e aguardar resultado do CI. Por instrução expressa, parar enquanto o CI executa e retomar somente quando o usuário retornar. Depois: inventário atualizado/portas/plano de impacto, publicação, UUID/grants e montagem/agendamento do snapshot de host. Inclui confirmação PostgreSQL do caso legado de concorrência que falha por lock no SQLite; não substituir essa validação por resultado simulado. Detalhes em `validation.md` e `docs/system-monitor.md`.

## Workflow follow-up
- Revisão humana antes de sincronizar specs e arquivar.
