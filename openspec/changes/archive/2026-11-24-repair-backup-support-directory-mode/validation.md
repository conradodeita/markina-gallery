# Validação

## Validação local — 24/11/2026

- Após ajustar o fixture POSIX, `python -m unittest test_production_app_preflight_support.py test_production_app_preflight_support_workflow.py` — 49 testes passaram; 2 testes POSIX foram ignorados no Windows. A chamada sintética `Path.lstat` foi verificada em execução local; os dois cenários POSIX passaram no runner Linux em `45449415944`.
- `ruff check scripts/production_app_preflight_support.py scripts/test_production_app_preflight_support.py scripts/test_production_app_preflight_support_workflow.py` — passou.
- `python scripts/test_production_release_workflow_policy.py` — passou (`publication_candidate_ready=false / arquivo_fora_do_escopo`; política concluída como `ok`).
- `openspec validate repair-backup-support-directory-mode --strict` e `git diff --check` — passaram após a correção do fixture.
- Parse YAML do workflow `production-app-compose-bridge-install.yml` — passou na validação anterior; o workflow não mudou nesta correção.
- `bash -n` não foi reexecutado nesta máquina nesta revisão: o comando `bash` disponível encaminha ao WSL e não há `/bin/bash`; a validação anterior do runner por Git Bash permanece aplicável porque nenhum script shell ou workflow mudou.
- `bash -n` no runner `scripts/install-prod-app-compose-bridge.sh` e no bloco `run` do job protegido passou usando Git Bash antes desta correção; nenhum script shell ou workflow mudou.
- Revisão do diff deste ajuste não identificou código morto, duplicação ou conteúdo semelhante a segredo; o único arquivo de código alterado é o fixture POSIX.

## CI da PR #425 — 24/11/2026

- Run `45449415944`, SHA `7a509abf743c4a76b5719ff68033e52dc8268227` — success.
- `homolog-inventory-policy` e `gemma-runtime` — success. Os testes POSIX `test_backup_mode_repair_preserves_directory_identity_and_contents` e `test_backup_mode_repair_fails_closed_if_path_identity_changes_after_chmod` passaram no runner Linux; a suíte focada do suporte registrou 49 testes, todos aprovados.
- `backend-tests` (shards 0–3), `backend-quality`, frontend, imagens amd64/arm64, OpenSpec, `ci-scope` e Gitleaks — success. Jobs de produção ficaram skipped pela classificação de escopo da PR.
- Esta evidência conclui as tasks 1.1 e 1.2. A CI da branch não conclui a task 3.1, que exige revisão humana, integração autorizada e nova CI verde na `main` no SHA integrado.

## Integração e CI da main — 24/11/2026

- PR #425 foi integrada com merge commit `e8b36204d9467914cfc9da90b5dcaabda087998a`; branch remota preservada.
- Run da `main` `45458633617`, SHA `e8b36204d9467914cfc9da90b5dcaabda087998a` — success. Passaram frontend, imagens amd64/arm64, backend-quality, shards backend 0–3, `homolog-inventory-policy`, `gemma-runtime`, OpenSpec, Gitleaks e `ci-scope`; jobs operacionais de produção ficaram skipped.
- A revisão humana, integração e CI verde da `main` concluem a task 3.1. Nenhum workflow foi despachado e nenhum host, Drive, pasta de backup, runtime, serviço ou timer foi acessado ou alterado.

## Limitações e gates pendentes

- A primeira CI da PR, run `45439480887` no SHA `31105891f45fc54de9eb38a1b3116331b51678a0`, executou os testes POSIX e falhou em dois casos porque a guarda de plataforma comparava `os.stat` com identidade em `os.supports_dir_fd` enquanto o teste o substituía para sintetizar ownership. A checagem rejeitou o runner antes de chamar `fchmod`; os outros testes focados passaram.
- A segunda CI, run `45444285674` no SHA `9ee976e29297402aadbef70378dc128a74e26d78`, passou os quatro shards backend, mas `homolog-inventory-policy` falhou nos dois testes POSIX novos: o fixture sintetizava ownership para `os.stat`/`os.fstat`, mas a validação inicial também usa `Path.lstat`, que retornou o UID/GID real do runner e bloqueou antes de `fchmod`. `gemma-runtime` falhou em cascata. O fixture foi corrigido para sintetizar também `Path.lstat`; o conteúdo da rotina de produção não mudou. A terceira CI Linux, run `45449415944`, confirmou os dois cenários POSIX e concluiu verde.
- Qualquer uso futuro da operação ainda exige novo `support-inventory`, revisão da fingerprint atual, autorização operacional específica e aprovação do ambiente `production`; após a correção, será necessário outro inventário antes de `prepare-support`.
