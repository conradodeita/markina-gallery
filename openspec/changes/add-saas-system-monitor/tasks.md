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

Estado de 6.2: PR #151 publicado no SHA 777495b; migration 0072, proprietário/grants e coleta ativados. Host Python 3.8 exigiu correção do CLI, já validada e instalada como cópia standalone privada. Fonte/SQL/lock PostgreSQL/relatório sanitizado/negação HTTP anônima e jornada normal do proprietário (árvore, filtro/busca, exportação JSON/texto, card) verificados remotamente. A abertura inicial expôs 429 por três chamadas concorrentes disputando duas leituras: regressão reproduzida e corrigida na interface, com validação unitária. Restam publicação dos ajustes de runtime/persistência/fila da interface, CI e repetição da abertura inicial e preservação de coleta/versão no servidor após deploy. Nenhuma credencial extraída ou sessão fabricada. O cenário de concorrência SQLite foi aprovado na suíte PostgreSQL do CI. Por instrução expressa, parar após push enquanto CI executa e retomar quando o usuário retornar. Detalhes em `validation.md`, inventário e `docs/system-monitor.md`.

## Workflow follow-up
- Deploy 38018392420 falhou antes da publicação por definição incompleta do worker de prévias no preflight; os quatro checks de código passaram. Servidor healthy no SHA 70716c1, porém monitor desativado pelo deploy anterior sem overlay. Correção do wrapper validada na matriz shell e com Compose real somente leitura; aguardará novo PR/CI e publicação antes de repetir a jornada e concluir 6.2. Detalhes atualizados em `validation.md`.
- PR #153 confirmado verde no HEAD 6036598 e mesclado em develop no SHA aea147f. CI/deploy 38018392420 em execução; pausa expressa do proprietário. Retomar 6.2 após retorno com o resultado, validar a publicação e a abertura inicial no servidor antes de concluir. Evidência da retomada registrada em `validation.md` (ainda local, para reconciliar na entrega final).
- Revisão humana antes de sincronizar specs e arquivar.
