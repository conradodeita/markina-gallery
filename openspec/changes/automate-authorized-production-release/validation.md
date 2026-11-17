# Validação — continuidade de release autorizado

## Checkpoint local — 07/11/2026

- `backend/tests/test_app_env_transition_inventory.py`: **2 passed** após reconciliar a matriz de referências com os módulos atuais (`google_drive_oauth`, `google_drive_storage`, onboarding, signup, backup/archive, campos privados e credenciais WhatsApp por tenant). A falha inicial mostrou drift da matriz; não houve alteração no comportamento de runtime para silenciá-la.
- `scripts/test_release_candidate_policy.py`: **9 testes aprovados**.
- `scripts/test_verify_main_ci_evidence.py` via pytest: **7 passed**. Executar esse arquivo como script direto falha por resolução do pacote `scripts`; a invocação de teste correta foi `python -m pytest`.
- `scripts/test_production_release_workflow_policy.py`: `production release workflow policy: ok`. O snapshot real do checkout informou `publication_candidate_ready=false / arquivo_fora_do_escopo`; o worktree contém várias changes SaaS locais fora do manifesto desse candidato, então não está pronto para abrir um draft PR a partir deste estado.
- `openspec validate automate-authorized-production-release --strict --json`: **válido, 0 issues**.
- Não houve workflow dispatch, publicação de PR, aprovação de environment protegido, execução remota, migration, deploy ou acesso a produção/homologação.
- Permanecem bloqueados os itens que exigem comprovar o encadeamento completo no runner e a aprovação do executor autorizado (2.2/3.1), além de publicar/acompanhar o draft PR após reconciliar o SHA de base e o candidato (3.2). A evidência local não substitui esses gates.

## Revisão local — 08/11/2026

- Matriz focada local, com `PYTHONPATH=scripts`: inventário APP_ENV (2), política do candidato (9), evidência de CI (7) e contrato do workflow manual rápido (5): **23 passed**. A primeira coleta identificou que `photographer_onboarding.py` tem quatro linhas de leitura `APP_ENV`; a matriz esperava três. A expectativa foi atualizada para refletir a leitura adicionada no aceite de Termos; nenhum comportamento do runtime foi alterado.
- `python scripts/test_production_release_workflow_policy.py`: `production release workflow policy: ok`; o candidato local continua corretamente recusado como `arquivo_fora_do_escopo`.
- `ruff check backend/tests/test_app_env_transition_inventory.py`, `git diff --check` do escopo e `openspec validate automate-authorized-production-release --strict`: passaram.
- Revisão do fluxo confirmou: disparo somente manual na `main`; CI de suporte read-only; inventário sob ambiente `production-preflight`; execução depende da confirmação de autorização e do environment `production`, usa o fingerprint produzido no mesmo preflight e passa esse valor ao executor, que compara inventário atualizado sob lock antes de iniciar a etapa mutável. A prova real no runner e da aprovação protegida não foi executada.
- `scripts/test_preview_adjustment_migration_release_flow.py`, `scripts/test_preview_adjustment_migration_inventory.py` e `scripts/test_fast_preview_release.py`: **33 passed**. Cobrem fingerprint de aprovação inválido, mudança de estado sob lock, falha antes de mutação, escopo limitado do workflow e continuidade dos passos operacionais revisados. São provas sintéticas locais, não execução no runner GitHub.
- Não houve push/PR, dispatch, aprovação de environment, chamada SSH, migration, deploy ou acesso a produção. A task 2.2 continua aberta até a prova no runner; 3.2 continua sem publicação.
