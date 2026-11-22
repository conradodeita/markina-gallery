# Tasks

- [x] 1.1 Inventariar migrations com guards de preservação, tabelas consultadas/alvo e escritores ativos; reconciliar ownership com as changes OpenSpec.
- [x] 1.2 Definir falha fechada com ACCESS EXCLUSIVE NOWAIT antes dos guards, mantendo a exigência existente de quiescência operacional.
- [x] 2.1 Atualizar os 32 downgrades protegidos entre 0094–0126 para adquirir o conjunto completo de locks antes de qualquer guard ou DDL; preservar a cobertura existente de 0094/0095 e fazê-la falhar sem espera.
- [x] 2.2 Acrescentar regressão PostgreSQL descartável para conflito de lock, mantendo os testes existentes de recusa com dados e downgrade vazio.
- [x] 3.1 Executar regressão estática, Ruff e validação OpenSpec estrita.
- [x] 3.2 Executar a regressão de lock e os cenários PostgreSQL de recusa/vazio em banco descartável exclusivo. A autorização local posterior do proprietário substituiu a restrição de início deste checkpoint; provas de 15/11 em `validation.md`, sem migration remota.
- [x] 3.3 Revisar o diff final, confirmar AST de `upgrade()` e guards/DDL preservados, e registrar limitações; baseline histórico completo e proveniência em `validation.md` e no artefato migration-baseline-pre-locks-20261115.
