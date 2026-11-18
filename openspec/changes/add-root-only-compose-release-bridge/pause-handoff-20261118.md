# Checkpoint do PR #384 após a primeira CI

Atualizado em 18/11/2026. O primeiro run do PR terminou; a correção local está em andamento. Nenhum teste Docker está ativo localmente.

## Estado do repositório

- Worktree: `C:\codex-data\worktrees\saas-release-candidate\Photo Delivery`.
- Branch `fix/prove-received-app-engine-runtime`, HEAD remoto/local base `3b3996509f23aae60543f4b87ec4c2d93d0d247a`, PR aberto: https://github.com/conradodeita/markina-gallery/pull/384.
- Alterações locais ainda sem commit: adapter do CLI Docker somente no harness descartável, quatro testes unitários desse adapter e evidências em `design.md`, `tasks.md` e `validation.md`. O arquivo não rastreado `output` é preexistente e fica fora do stage.
- A branch já inclui o merge limpo da `main` #383 (`4d78f6a`). Não rebasear nem usar force push.

## CI do PR

- Run `44411391749` terminou vermelho. OpenSpec, Gitleaks, escopo, frontend, imagens AMD64/ARM64 e os três shards completos de backend passaram.
- O único erro direto no job de qualidade foi a prova Engine, encerrada em 19 s com `protected_command_failed`. Traceback minimizado passou por `_engine_discover`, `_inspect_api_web`, `_list_service_ids`, `_docker` e `_run`, no tratamento `OSError`/timeout. O tempo exclui o timeout de 120 s. Os comandos do harness via `PATH` criaram os fixtures; a hipótese é que o `/usr/bin/docker` fixo usado pela ponte não exista/seja executável nesse runner. A causa é inferida porque a mensagem root-only omite o detalhe do `OSError`.
- A correção local tenta `/usr/bin/docker` primeiro e, somente se não executável, resolve um caminho absoluto via `shutil.which` dentro da prova descartável; as chamadas continuam pelo mesmo `_run` limitado. O helper de produção não mudou e mantém `/usr/bin/docker` fixo.

## Validação local da correção

- A suíte completa da ponte passou com 54 testes e 1 skip de symlink real indisponível no Windows; os quatro testes do adapter estão incluídos.
- Ruff e `py_compile` dos arquivos alterados, OpenSpec estrito e `git diff --check` passaram após o último ajuste.
- Não execute `scripts/prove_app_engine_promotion.py` nesta máquina: Docker é compartilhado com outros projetos. A integração real pertence ao runner GitHub-hosted descartável.

## Produção e serviços laterais

- Nenhuma alteração de produção ocorreu. Nenhum deploy, `.env`, secret, banco, migration, worker, backup ou fila foi tocado.
- Este deploy API/web não instala/inicia `pyp-platform-backup.service`/`.timer` nem retoma workers/filas. O retorno do backup e da fila original não tem data marcada; depende de mudança/plano separado após o release e autorização própria.
- O preflight somente-leitura de `main` `44392683081` continua sem fingerprint e sem causa confirmada; não confundir com a falha de CLI da prova Engine.

## Próximas ações

1. Revisar o diff restrito; a suíte completa da ponte, Ruff, compilação, OpenSpec estrito e diff check já passaram.
2. Criar um commit Conventional somente com a correção/handoff desta change e fazer um único push ao branch do PR #384.
3. Acompanhar a nova CI. Reutilizar jobs no mesmo SHA quando houver falha elegível; não iniciar workflows de instalação/release.
4. Manter tasks 5.2–5.4 e 6.1–6.3 abertas até prova Engine real e gates protegidos.
