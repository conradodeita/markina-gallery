# Checkpoint do PR #384 após a terceira CI

Atualizado em 18/11/2026. Nenhuma prova Docker está ativa localmente. O CI `44424649626` terminou; uma segunda causa no harness foi corrigida localmente e passou os gates focados, ainda sem commit/push.

## Estado do repositório

- Worktree: `C:\codex-data\worktrees\saas-release-candidate\Photo Delivery`.
- Branch `fix/prove-received-app-engine-runtime`, HEAD remoto/local `25fc7f7ef829e66034af7077c97667144bbc7dee`; PR #384: https://github.com/conradodeita/markina-gallery/pull/384.
- Alterações locais: `scripts/prove_app_engine_promotion.py` adapta `cwd` implícito e o default de projeto do seletor somente após `require_ci_runner()`; testes cobrem `cwd` implícito/explicito, projeto sintético corrente, argumento explícito e adaptador do CLI; design, tasks e validação registram diagnósticos/evidências.
- `output` já existia sem rastreamento e fica fora do stage/commit.
- Não rebasear nem usar force push.

## CI do PR

- Run `44424649626` no SHA `25fc7f7ef829e66034af7077c97667144bbc7dee` falhou no passo da prova Engine com `api_web_container_count_invalid`; os três shards do backend passaram. OpenSpec, escopo, Gitleaks, frontend e imagens AMD64/ARM64 também passaram. Agregados/políticas dependentes falharam e jobs mutáveis de produção/homologação ficaram pulados.
- A adaptação de `cwd` eliminou o erro anterior e a prova avançou até `select_api_web`. Causa confirmada: `project=PROJECT` capturado no import permaneceu `markina-gallery` enquanto fixtures usam nome sintético por cenário.
- A correção local preserva os defaults de produção e mantém as chamadas sob o mesmo `_run` limitado. A prova Docker real só deve rodar no runner GitHub-hosted descartável dentro do job existente.

## Validação local

- `python -m unittest discover -s scripts -p test_production_app_compose_bridge.py`: 59 testes; 58 passaram e 1 skip de symlink real indisponível no Windows.
- Ruff, `py_compile`, OpenSpec estrito e `git diff --check` passaram.
- Não executar `scripts/prove_app_engine_promotion.py` nesta máquina; Docker é compartilhado com Oracle/outros projetos.

## Produção e serviços laterais

- Nenhuma operação remota ou mudança em produção ocorreu. Nenhum deploy, `.env`, secret, banco, migration, worker, backup, fila ou recurso compartilhado foi tocado.
- Este release API/web não instala/inicia `pyp-platform-backup.service`/`.timer` nem reativa workers/filas. O retorno continua sem data definida e requer change/plano separado, validação e autorização próprias.
- Preflight somente-leitura de `main` `44392683081` continua sem fingerprint e sem causa confirmada; não confundir com esta falha do CI de PR.

## Próximas ações

1. Revisar o diff exato, preservando o caminho `output` fora do stage.
2. Criar um commit Conventional restrito à correção e seus artefatos OpenSpec; fazer um único push normal ao PR #384.
3. Acompanhar a próxima CI até concluir; reutilizar somente jobs elegíveis se houver falha sem mudança de código.
4. Manter tasks 4.2, 5.2–5.4 e 6.1–6.3 abertas até prova Engine real, CI verde e gates protegidos.
