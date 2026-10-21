# Tasks

## 1. Contrato e controle

- [x] 1.1 Implementar controle Redis dedicado à manutenção e transições atômicas; testes cobrem modo ausente, entrada duplicada, operação sem ACK e retomada. Evidência: `backend/tests/test_maintenance_control.py` e `backend/tests/test_maintenance_integration.py`.
- [x] 1.2 Estender middleware ASGI para negar ingressos comuns, permitir healthchecks e admitir somente callbacks críticos por método/caminho exatos; testes cobrem 503 antes do handler e callbacks com ACK/falha. Evidência: `backend/tests/test_maintenance_control.py` e `backend/tests/test_maintenance_integration.py`.
- [x] 1.3 Estender CLI com início, status, drenagem e retomada explícitos; `maintenance-finish` exige recibos Redis e estados persistidos vazios. Evidência: `backend/tests/test_maintenance_cli.py`.
- [x] 1.4 Documentar ativação opt-in, comandos de manutenção, semântica de retomada e bloqueios de bootstrap/callback em `docs/CONTROLLED-MAINTENANCE.md`; testes do CLI confirmam início e retomada controlados.

## 2. Workers, filas e operações em voo

- [x] 2.1 Verificar cobertura dos oito consumidores Python: API, worker geral, facial search/index/Gemma/maintenance, preview e RAW; Compose entrega a flag a todos. Teste confirma que ciclo não inicia durante gate e retoma depois.
- [x] 2.2 Exercitar upload em voo, sessão existente, callback válido/falho, ciclo de worker, falha antes do ACK, fila persistente e retomada; suíte com serviços PostgreSQL 16/Redis 7 descartáveis e regressões InfinitePay/WhatsApp: 29 testes passaram. CI provisiona os serviços descartáveis para não pular as integrações reais.
- [x] 2.3 Revisar handlers financeiros e de mensagem apenas quanto ao contrato da middleware; não alterar regra de negócio nem o PR #260. Regressões do retorno InfinitePay e webhook WhatsApp passaram; retry/reconciliação durante troca da API permanece não comprovado.

## 3. Bootstrap e integração

- [x] 3.1 Registrar a avaliação concreta do bootstrap legado e manter NO-GO: processos atuais não consultam gate; não há pausa de claims nem ACK verificável antes da primeira substituição. Nenhum processo ou Oracle foi alterado.
- [x] 3.2 Executar testes direcionados, OpenSpec strict, Ruff/compileall, configuração Compose e revisão do diff escopado; sem refatoração elegível fora da change. Evidência: `validation.md`.
- [ ] 3.3 Isolar a change em worktree e branch próprios, revisar o diff para excluir alterações experimentais do release Python e preparar um PR draft com evidências locais aprovadas. O draft solicita revisão da funcionalidade; não autoriza ativação, release ou merge.
- [ ] 3.4 Concluir revisão humana antes de sincronizar a spec principal, retirar o draft ou arquivar a change. Primeiro bootstrap legado e continuidade dos callbacks durante parada da API continuam bloqueios operacionais explícitos.

## Workflow follow-up

- Sincronizar a spec principal e arquivar somente após revisão humana.
- Qualquer bootstrap/release operacional exige missão e autorização separadas, prova dos gates, continuidade de callbacks e revisão do PR #260 concluída pelo executor responsável.
