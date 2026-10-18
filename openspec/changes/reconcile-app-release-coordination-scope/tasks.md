# Tasks

## 1. Reconciliar o escopo de release

- [x] 1.1 Incluir os quatro caminhos exatos de coordenação de release na allowlist operacional e adicionar testes positivos por caminho e teste negativo para caminho semelhante não listado. Evidência: `python scripts/test_prod_app_release_scope.py -v` — 10 testes aprovados, incluindo a allowlist exata e rejeição de script parecido não listado.
- [x] 1.2 Validar a política contra o SHA integrado, confirmar que runtime blobs e manifestos permanecem inalterados e registrar o resultado do CI que motivou a correção. Evidência: `python scripts/check_prod_app_release_scope.py --base b4f15abd6a71585082758062feba7fcfcc225587 --target origin/main` retornou `app_release_ready=true`, `somente_api_web`; OpenSpec estrito e `git diff --check` passaram. O manifesto de runtime, baseline, schema e gates não foram alterados.
