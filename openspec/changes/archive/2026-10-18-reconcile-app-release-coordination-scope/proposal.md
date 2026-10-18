# Reconciliação do escopo de release API/web

## Why

O preflight do SHA integrado `dfbf2c94706dd98f31ca362daac328ad22e79651` recusou o release antes de acessar o host, pois o diff desde o baseline saudável contém quatro arquivos exatos da mudança já aprovada de exclusão mútua dos releases API/web e web-only. O verificador reconhece o delta da aplicação, mas sua allowlist de operações não inclui esses arquivos.

## What Changes

- Permitir no verificador do release API/web somente os quatro caminhos operacionais e testes já revisados na change `coordinate-production-api-web-release`.
- Cobrir cada caminho permitido e manter caminhos operacionais não listados recusados.
- Registrar que essa reconciliação de escopo não altera runtimes, manifesto, baseline, schema ou gates de aprovação.

## Impact

- Specs afetadas: `deployment-operations`.
- Código e testes: `scripts/check_prod_app_release_scope.py` e `scripts/test_prod_app_release_scope.py`.
- Não altera containers, dados, migrations, API, frontend, workers ou comportamento do produto.
