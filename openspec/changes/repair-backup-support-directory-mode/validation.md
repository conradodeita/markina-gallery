# Validação

## Validação local — 24/11/2026

- Após ajustar o fixture POSIX, `python -m unittest test_production_app_preflight_support.py test_production_app_preflight_support_workflow.py` — 49 testes passaram; 2 testes POSIX foram ignorados no Windows. A chamada sintética `Path.lstat` foi verificada em execução local; a semântica POSIX completa aguarda o runner Linux.
- `ruff check scripts/production_app_preflight_support.py scripts/test_production_app_preflight_support.py scripts/test_production_app_preflight_support_workflow.py` — passou.
- `python scripts/test_production_release_workflow_policy.py` — passou (`publication_candidate_ready=false / arquivo_fora_do_escopo`; política concluída como `ok`).
- `openspec validate repair-backup-support-directory-mode --strict` e `git diff --check` — passaram após a correção do fixture.
- Parse YAML do workflow `production-app-compose-bridge-install.yml` — passou na validação anterior; o workflow não mudou nesta correção.
- `bash -n` não foi reexecutado nesta máquina nesta revisão: o comando `bash` disponível encaminha ao WSL e não há `/bin/bash`; a validação anterior do runner por Git Bash permanece aplicável porque nenhum script shell ou workflow mudou.
- `bash -n` no runner `scripts/install-prod-app-compose-bridge.sh` e no bloco `run` do job protegido passou usando Git Bash antes desta correção; nenhum script shell ou workflow mudou.
- Revisão do diff deste ajuste não identificou código morto, duplicação ou conteúdo semelhante a segredo; o único arquivo de código alterado é o fixture POSIX.

## Limitações e gates pendentes

- A primeira CI da PR, run `45439480887` no SHA `31105891f45fc54de9eb38a1b3116331b51678a0`, executou os testes POSIX e falhou em dois casos porque a guarda de plataforma comparava `os.stat` com identidade em `os.supports_dir_fd` enquanto o teste o substituía para sintetizar ownership. A checagem rejeitou o runner antes de chamar `fchmod`; os outros testes focados passaram.
- A segunda CI, run `45444285674` no SHA `9ee976e29297402aadbef70378dc128a74e26d78`, passou os quatro shards backend, mas `homolog-inventory-policy` falhou nos dois testes POSIX novos: o fixture sintetizava ownership para `os.stat`/`os.fstat`, mas a validação inicial também usa `Path.lstat`, que retornou o UID/GID real do runner e bloqueou antes de `fchmod`. `gemma-runtime` falhou em cascata. O fixture foi corrigido para sintetizar também `Path.lstat`; o conteúdo da rotina de produção não mudou. A terceira CI Linux ainda precisa confirmar os dois cenários POSIX.
- As tasks 1.1 e 1.2 permanecem pendentes até os testes POSIX passarem no runner Linux; a execução Windows não cobre os dois testes ignorados.
- A task 3.1 aguarda revisão humana, merge autorizado e CI verde da `main` no SHA exato. Nenhuma operação remota foi despachada; nenhum host, Drive, diretório de backup ou serviço/timer foi acessado ou alterado.
- Depois da integração, a operação continua exigindo novo `support-inventory`, revisão de fingerprint atual, autorização operacional específica e aprovação do ambiente `production`; após a correção, será necessário outro inventário antes de `prepare-support`.
