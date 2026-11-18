# Checkpoint do PR #384 após a segunda CI

Atualizado em 18/11/2026. Nenhuma prova Docker está ativa localmente. O CI `44418238541` terminou; a correção local de contexto do runner foi implementada e passou os gates focados, ainda sem commit/push.

## Estado do repositório

- Worktree: `C:\codex-data\worktrees\saas-release-candidate\Photo Delivery`.
- Branch `fix/prove-received-app-engine-runtime`, HEAD remoto/local `9380992bb86828e85dd480f77e4297e6fc4203fb`; PR #384: https://github.com/conradodeita/markina-gallery/pull/384.
- Alterações locais: `scripts/prove_app_engine_promotion.py` adapta o `cwd` implícito da ponte para a raiz do checkout somente após `require_ci_runner()`; testes cobrem `cwd` implícito/explicito e o adaptador de CLI; design, tasks e validação registram o diagnóstico e evidências.
- `output` já existia sem rastreamento e fica fora do stage/commit.
- Não rebasear nem usar force push.

## CI do PR

- Run `44418238541` no SHA `9380992bb86828e85dd480f77e4297e6fc4203fb` terminou com falha no passo da prova Engine após 16 s. Gitleaks, OpenSpec, escopo, frontend, imagens AMD64/ARM64 e os três shards do backend passaram; o agregado e os jobs dependentes falharam em consequência.
- A hipótese anterior de caminho `/usr/bin/docker` não explicou a falha. O código mostra que `_run` captura `/opt/markina-gallery` como default de `cwd` no import, embora o runner use outra raiz. Isso é a hipótese dominante para o `OSError` minimizado, não uma causa confirmada.
- A correção local preserva os defaults de produção e mantém todas as chamadas sob o mesmo `_run` limitado. A prova Docker real só deve rodar no runner GitHub-hosted descartável dentro do job existente.

## Validação local

- `python -m unittest discover -s scripts -p test_production_app_compose_bridge.py`: 57 testes; 56 passaram e 1 skip de symlink real indisponível no Windows.
- Ruff, `py_compile`, OpenSpec estrito e `git diff --check` passaram.
- Não executar `scripts/prove_app_engine_promotion.py` nesta máquina; Docker é compartilhado com Oracle/outros projetos.

## Produção e serviços laterais

- Nenhuma operação remota ou mudança em produção ocorreu. Nenhum deploy, `.env`, secret, banco, migration, worker, backup, fila ou recurso compartilhado foi tocado.
- Este release API/web não instala/inicia `pyp-platform-backup.service`/`.timer` nem reativa workers/filas. O retorno continua sem data definida e requer change/plano separado, validação e autorização próprias.
- Preflight somente-leitura de `main` `44392683081` continua sem fingerprint e sem causa confirmada; não confundir com esta falha do CI de PR.

## Próximas ações

1. Revisar o diff exato, preservando o caminho `output` fora do stage.
2. Criar um commit Conventional restrito à correção e seus artefatos OpenSpec; fazer um único push normal ao PR #384.
3. Acompanhar a CI nova até concluir; reutilizar somente jobs elegíveis se houver falha sem mudança de código.
4. Manter tasks 4.2, 5.2–5.4 e 6.1–6.3 abertas até prova Engine real, CI verde e gates protegidos.
