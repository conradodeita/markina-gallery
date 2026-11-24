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

## Task 3.1 — preflight de publicação — 24/11/2026 BRT

- `origin/main` e a base da branch coincidem em `bc96fcda3172b73fe452f8fc98ebc3d7fcb86932`; a CI da main `45311450221` terminou success nesse SHA exato.
- `gh` está autenticado para o repositório. Gitleaks não está instalado localmente; o diff foi revisado manualmente e a verificação remota de segredos permanece pendente na CI da PR.

## Task 2.1 — integração local — 24/11/2026 BRT

- `python scripts/test_production_app_preflight_support.py`: 44 testes passaram.
- `python scripts/test_production_app_preflight_support_workflow.py`: passou.
- `ruff check scripts/production_app_preflight_support.py scripts/test_production_app_preflight_support.py scripts/test_production_app_preflight_support_workflow.py`: passou.
- `openspec validate diagnose-support-storage-readiness --strict`: change válida.
- `git diff --check`: passou. A busca de espaços em branco finais nos artefatos novos não encontrou ocorrências; Git apenas avisou que normalizará LF para CRLF nos arquivos Python em futuras operações.
- Revisão do diff: somente o classificador read-only, a saída allowlisted e os testes correspondentes mudaram. Os estados agregados e `_assert_storage_preconditions` permanecem intactos; nenhuma credencial, valor bruto do filesystem ou dado de cliente foi adicionado. Nenhuma limpeza além da deduplicação do classificador era segura ou necessária.
- A CI remota ainda não foi executada; seguirá após publicação da branch e criação da PR.
