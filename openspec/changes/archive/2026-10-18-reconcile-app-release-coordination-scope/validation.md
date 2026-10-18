# Validação

## Evidência do bloqueio

- Após o merge da PR #223, o CI do SHA `dfbf2c94706dd98f31ca362daac328ad22e79651` executou OpenSpec, frontend, gitleaks, políticas de inventário e backend com sucesso. `pytest` e as regressões concorrentes PostgreSQL passaram.
- `production-app-preflight` parou em `Validar escopo e blobs revisados` antes de qualquer SSH/inventário remoto: `app_release_ready=false`, `criterio=arquivo_fora_do_escopo`.
- A comparação entre o baseline saudável `b4f15abd6a71585082758062feba7fcfcc225587` e o alvo integrado identificou quatro caminhos exatos omitidos da allowlist: `scripts/deploy-prod-lock.sh`, `scripts/deploy-prod-web.sh`, `scripts/test_deploy_prod_web.sh` e `scripts/test_deploy_prod_web_policy.py`. Esses arquivos são da change já revisada `coordinate-production-api-web-release`; não alteram runtimes de API/web.

## Correção e validação local

- A allowlist operacional passou a incluir somente os quatro caminhos acima. Foi mantido um teste negativo para `scripts/deploy-prod-unreviewed.sh`.
- `python scripts/test_prod_app_release_scope.py -v`: 10 testes aprovados.
- `python scripts/check_prod_app_release_scope.py --base b4f15abd6a71585082758062feba7fcfcc225587 --target origin/main`: `app_release_ready=true`, `criterio=somente_api_web`.
- `npx openspec validate reconcile-app-release-coordination-scope --strict`: change válida.
- A validação ampla `npx openspec validate --all --strict` retornou 92 itens válidos e 30 falhos em outras changes/specs existentes; a validação específica desta change passou. Os avisos/erros abrangem deltas já duplicados e requisitos longos fora do escopo desta correção e não foram alterados.
- `git diff --check`: aprovado.
- O manifesto de blobs de runtime, baseline saudável, revisão do banco, portas, serviços e gates de aprovação não foram modificados. Nenhuma conexão SSH, inventário remoto, alteração de host ou publicação foi executada nesta correção.

## Integração e publicação concluídas

A PR #224 passou nos checks e foi integrada como `fe1f3bc6e1a483bd1ac5f4e71149f903e724873f`. O CI de `main` aprovou backend, frontend, OpenSpec e políticas; a tentativa 1 parou no wrapper desatualizado. Após a atualização verificada, o run `39135274157`, tentativa 2, passou no inventário e publicou API/web com aprovação protegida. O run terminou verde, o checkout ativo corresponde ao alvo, o schema permaneceu `20261017_0084` e os serviços ficaram saudáveis. Evidências em `docs/RELEASE-SALES-PAYMENTS-20261018.md`.

Após a publicação confirmada, o baseline foi avançado para o SHA saudável; os blobs de runtime e gates faciais permaneceram iguais. A spec principal foi sincronizada para arquivamento após a revisão humana recebida.
