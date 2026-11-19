# Checkpoint do PR #384 após a quarta CI

Atualizado em 18/11/2026. Nenhuma prova Docker está ativa localmente. O CI `44428285088` terminou; a revisão do baseline sintético foi corrigida localmente e passou os gates focados, ainda sem commit/push.

## Estado do repositório

- Worktree: `C:\codex-data\worktrees\saas-release-candidate\Photo Delivery`.
+ Branch `fix/prove-received-app-engine-runtime`, HEAD remoto/local `b36c38087cacd087d768527938a6d44d87b18235`; PR #384: https://github.com/conradodeita/markina-gallery/pull/384.
+ Alterações locais: `scripts/prove_app_engine_promotion.py` adapta `cwd` implícito, seletor de projeto e revisão antiga do fixture; testes cobrem esses contratos, `cwd` explícito, projeto explícito e CLI. Design, tasks e validação registram diagnósticos/evidências.
- `output` já existia sem rastreamento e fica fora do stage/commit.
- Não rebasear nem usar force push.

## CI do PR

+ Run `44428285088` no SHA `b36c38087cacd087d768527938a6d44d87b18235` falhou na prova Engine com `engine_original_pair_mismatch`. Os três shards do backend passaram, assim como OpenSpec, escopo, Gitleaks, frontend e imagens AMD64/ARM64; agregados/gates dependentes falharam e os jobs mutáveis ficaram pulados.
+ As adaptações de `cwd` e do seletor permitiram à prova chegar à comparação do par inicial. Causa confirmada: o `OLD_REVISION` sintético `"1"*40` não correspondia a `ENGINE_BOOTSTRAP_SHA` fixo do helper. A correção local deriva a revisão do fixture desse valor fixo.
+ O helper de produção permanece intacto; a prova Docker real só deve rodar no runner GitHub-hosted descartável dentro do job existente.

## Validação local

+ `python -m unittest discover -s scripts -p test_production_app_compose_bridge.py`: 60 testes; 59 passaram e 1 skip de symlink real indisponível no Windows.
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
