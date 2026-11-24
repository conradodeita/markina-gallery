# Validação

## Validação local — 24/11/2026

- `python -m unittest test_production_app_preflight_support.py test_production_app_preflight_support_workflow.py` — 49 testes passaram; 2 testes de descritores e semântica POSIX foram ignorados no Windows. Esses testes exercitam a alteração real por descritor e a divergência de identidade e aguardam execução no runner Linux da CI.
- `ruff check scripts/production_app_preflight_support.py scripts/test_production_app_preflight_support.py scripts/test_production_app_preflight_support_workflow.py scripts/test_production_release_workflow_policy.py` — passou.
- `python scripts/test_production_release_workflow_policy.py` — passou.
- Parse YAML do workflow `production-app-compose-bridge-install.yml` — passou.
- `bash -n` no runner `scripts/install-prod-app-compose-bridge.sh` e no bloco `run` do job protegido — passou usando Git Bash.
- `openspec validate repair-backup-support-directory-mode --strict` — passou.
- `git diff --check` — passou; revisão do diff não identificou duplicação ou código morto na área alterada.
- A varredura local por padrões de segredo conhecidos não encontrou correspondências nos arquivos alterados.

## Limitações e gates pendentes

- A primeira CI da PR, run `45439480887` no SHA `31105891f45fc54de9eb38a1b3116331b51678a0`, executou os testes POSIX e falhou em dois casos porque a guarda de plataforma comparava `os.stat` com identidade em `os.supports_dir_fd` enquanto o teste o substituía para sintetizar ownership. A checagem rejeitou o runner antes de chamar `fchmod`; os outros testes focados passaram. `gemma-runtime` falhou em cascata depois do gate `homolog-inventory-policy`. A guarda frágil foi removida; a nova CI Linux permanece pendente.
- A task 3.1 aguarda revisão humana, merge autorizado e CI verde da `main` no SHA exato. Nenhuma operação remota foi despachada; nenhum host, Drive, diretório de backup ou serviço/timer foi acessado ou alterado.
- Depois da integração, a operação continua exigindo novo `support-inventory`, revisão de fingerprint atual, autorização operacional específica e aprovação do ambiente `production`; após a correção, será necessário outro inventário antes de `prepare-support`.
