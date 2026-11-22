# Tasks

## 1. Modelo e precondições

- [x] 1.1 Reconciliar os consumidores de exclusão local, arquivo frio, recuperação e CPF; registrar em `validation.md` como o novo fluxo reutiliza cada contrato sem criar outra fila ou apagar registros comerciais. Evidência estática dos módulos, contratos e mudança de arquivo frio registrada em 10/11/2026; o runtime real não foi acionado.
- [x] 1.2 Acrescentar lote/itens de exclusão, checkpoint por objeto e nulabilidade do verificador CPF em migration aditiva; validar constraints, isolamento, upgrade e downgrade protegido em PostgreSQL descartável. Prova em PostgreSQL 17.11 temporário: upgrade/downgrade, preservação de legado, FKs de tenant/operação, contagens, CPF e recusas de perda de lotes/checkpoints/auditorias passaram. Campos de estado da auditoria ampliados a 32 caracteres para comportar retry integralmente.
- [x] 1.3 Implementar preflight tenant-scoped que exige conta `closed`, aniversário UTC de dez anos vencido, ao menos um ciclo de arquivo comprovado, todos os ciclos arquivados e ausência de operação pendente; testar que qualquer bloqueio — inclusive inventário/ciclo ausente — impede todos os efeitos e preserva o CPF. Validação: testes sintéticos de preflight, incluindo mídia registrada sem ciclo, passaram; nenhum lote é criado e o CPF permanece.

## 2. Ação e execução auditadas

- [x] 2.1 Integrar início, consulta e retry no console API do `PlatformOwner`, com senha, TOTP, frase explícita, mesmo-origin, rate limit, idempotência e eventos auditáveis; testar negação por papel, prazo, sessão, estado e tenant divergentes. Validação: `test_platform_console_media_deletion.py` passou dentro da bateria focada.
- [x] 2.2 Executar `delete_remote` na fila global existente, abaixo de restore e acima de archive, validando manifesto, conteúdo, SHA-256, remoção e readback ausente de cada objeto; cobrir retomada idempotente, falha parcial, resultado incerto e adapter sintético sem chamadas reais. Validação: executor e worker passaram nos testes sintéticos da bateria focada.
- [x] 2.3 Concluir lote/ciclo somente com todos os recibos, preservar histórico e bloquear recuperação/reabertura depois de `deleted`; remover somente fingerprint e versão do CPF após prova agregada completa; testar retries, falha parcial, idempotência e não remoção prematura. Validação: testes de exclusão e recuperação passaram, incluindo falhas/retries e preservação de dados comerciais.

## 3. Console, integração e fechamento

- [x] 3.1 Exibir elegibilidade, estado, contagens e erro sanitizado no console privado; exigir nova reautenticação e confirmação para retry; validar componentes e fluxos frontend sem expor PII, conteúdo ou IDs remotos. Validação: 7 testes do console passaram, com TypeScript e ESLint focalizados sem erros.
- [x] 3.2 Executar bateria integrada focada de exclusão/recuperação/encerramento, validação PostgreSQL descartável das migrations, Ruff, TypeScript, ESLint, build e `openspec validate --strict`; registrar evidências e revisar a área afetada por duplicação, código obsoleto e regressões sem tocar em Drive, produção, commit ou push. Bateria integrada: 70 passaram, sem skips, incluindo PostgreSQL. Checks de código e da change válidos; avisos globais preexistentes estão documentados em `validation.md`. Container temporário removido e porta liberada.
- [x] 3.3 Serializar retry administrativo com transições do worker pelo coordenador global antes de bloquear linhas do tenant/lote; regressão registra a ordem SQLAlchemy e confirma que o coordenador é o primeiro lock. Teste sintético local aprovado; a verificação não simula deadlock concorrente real em PostgreSQL.
- [x] 3.4 Revalidar `request_id` após o lock serializador do proprietário e antes de TOTP/mutação em exclusão, retry, redução de perfil, recuperação e reabertura; testes injetam resultado previamente confirmado após o lock e verificam replay sem nova ação.
