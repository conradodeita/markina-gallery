# Evidências de validação

## Task 1.1 — classificação e saída read-only — 24/11/2026 BRT

- `python scripts/test_production_app_preflight_support.py`: 44 testes passaram. Cobertura inclui estado agregado preservado, symlink sem dereferência, tipo/owner/grupo/modo, indisponibilidade sanitizada, allowlist de saída, ambos os modos de inventário, mudança de fingerprint por razão e bloqueio de preparação/restauração quando o estado é inseguro.
- `ruff check scripts/production_app_preflight_support.py scripts/test_production_app_preflight_support.py scripts/test_production_app_preflight_support_workflow.py`: passou.
- `python scripts/test_production_app_preflight_support_workflow.py`: passou.

## Task 1.2 — fronteira do workflow e refatoração — 24/11/2026 BRT

- O workflow protegido mantém as operações e permissões existentes, fixa o blob do helper à revisão e envia a saída do helper diretamente ao resumo por `tee`; a verificação estática agora exige esses campos diagnósticos e o formatter allowlisted.
- Não foi necessário alterar o workflow de produção: ele já apresenta a saída do helper sem transformá-la. Os dois inventários imprimem apenas categorias fixas; valores desconhecidos falham antes da linha de sucesso.
- Refatoração contínua: `_fixed_directory_state` agora delega ao classificador único que retorna estado e razões; `state_directory_status` e `backup_directory_status` permitem coletar cada par uma única vez no snapshot. Os métodos de criação e os gates continuam consultando os estados agregados. Nenhum outro código ficou elegível para remoção nesta área.
- Ainda pendentes neste ponto: validação de integração estrita, CI/PR/main e novo inventário remoto somente leitura; nenhuma ação no host foi executada.

## Task 2.1 — integração local — 24/11/2026 BRT

- `python scripts/test_production_app_preflight_support.py`: 44 testes passaram.
- `python scripts/test_production_app_preflight_support_workflow.py`: passou.
- `ruff check scripts/production_app_preflight_support.py scripts/test_production_app_preflight_support.py scripts/test_production_app_preflight_support_workflow.py`: passou.
- `openspec validate diagnose-support-storage-readiness --strict`: change válida.
- `git diff --check`: passou. A busca de espaços em branco finais nos artefatos novos não encontrou ocorrências; Git apenas avisou que normalizará LF para CRLF nos arquivos Python em futuras operações.
- Revisão do diff: somente o classificador read-only, a saída allowlisted e os testes correspondentes mudaram. Os estados agregados e `_assert_storage_preconditions` permanecem intactos; nenhuma credencial, valor bruto do filesystem ou dado de cliente foi adicionado. Nenhuma limpeza além da deduplicação do classificador era segura ou necessária.
- Na data desta validação local, a CI remota ainda não havia sido executada; o resultado posterior está registrado na Task 3.1.

## Task 3.1 — preflight de publicação — 24/11/2026 BRT

- `origin/main` e a base da branch coincidem em `bc96fcda3172b73fe452f8fc98ebc3d7fcb86932`; a CI da main `45311450221` terminou success nesse SHA exato.
- `gh` está autenticado para o repositório. Gitleaks não está instalado localmente; a revisão manual foi complementada pela verificação remota de segredos aprovada na CI da PR abaixo.
- PR #422, SHA `08303e7b94bf386d1437ab65a26f5cec681d4300`: CI `45391768675` terminou success. Gitleaks, OpenSpec, classificação de escopo, backend-quality, quatro shards backend, frontend, imagens AMD64/ARM64, `homolog-inventory-policy` e `gemma-runtime` passaram; jobs de produção foram ignorados pelo escopo. O resultado é válido para esse SHA; a integração e CI da main ainda estão pendentes.
- Após atualização documental, PR #422, SHA `e5875a8eb263e9ec21d015856633b986ab07415a`: CI `45395605397` terminou success, incluindo Gitleaks, OpenSpec, classificação de escopo, backend-quality, quatro shards backend, frontend, imagens AMD64/ARM64 e agregados `backend`, `homolog-inventory-policy` e `gemma-runtime`; jobs de produção foram ignorados pelo escopo. A integração e a CI da main ainda estão pendentes.
- PR #422 foi integrada por merge commit `d62ffde00959feb59756f38fcb9523602e0147d5` em 24/11/2026. A autorização expressa do proprietário para prosseguir e aprovar as etapas foi respeitada; não foi registrada revisão formal no GitHub. CI de push da `main` `45403526631` terminou success no SHA exato `d62ffde00959feb59756f38fcb9523602e0147d5`, com Gitleaks, OpenSpec, classificação de escopo, backend-quality, frontend, imagens AMD64/ARM64, quatro shards backend e agregados `backend`, `homolog-inventory-policy` e `gemma-runtime` aprovados.

## Task 3.2 — inventário remoto somente de leitura — 24/11/2026 BRT

- Run protegido `45407412507` executou somente `support-inventory` no SHA `d62ffde00959feb59756f38fcb9523602e0147d5`; a verificação de CI exata passou e o gate do ambiente `production` foi aprovado conforme a autorização expressa do proprietário para os próximos passos e aprovações.
- Resultado sanitizado: `support_inventory=success`; estado do diretório de estado `ready`, diagnóstico `ready`; diretório de backup `directory_invalid`, diagnóstico `target_mode_invalid`; fingerprint `5b4f5c1ccdd363acdabffbd6af8e7a042144e31ecb958a42ac6ed9bfbf90c2b4`.
- Nenhuma operação `prepare-support` ou reparo foi executada. Valores brutos de owner, grupo, modo, caminhos e conteúdo não foram registrados.

## Sincronização da capability — 24/11/2026 BRT

- A capability `deployment-operations/backup-runtime-support-diagnostics` não tinha spec principal; a spec foi criada por merge semântico do delta. A comparação verificou igualdade do propósito e do conteúdo integral dos requisitos/cenários.
- `openspec validate --specs`: 32 specs passaram; `openspec validate diagnose-support-storage-readiness --strict`: change válida; `git diff --check`: passou.
- O proprietário autorizou expressamente continuar e aprovar as próximas etapas. O PR não contém uma review formal registrada no GitHub; a autorização e a ausência do registro formal foram documentadas em `tasks.md`.
