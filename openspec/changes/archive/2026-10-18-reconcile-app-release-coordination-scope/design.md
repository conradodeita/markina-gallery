# Design

O baseline de produção é `b4f15abd6a71585082758062feba7fcfcc225587`. O SHA integrado também inclui a change já revisada `coordinate-production-api-web-release`, cuja exclusão mútua depende destes caminhos operacionais exatos:

- `scripts/deploy-prod-lock.sh`
- `scripts/deploy-prod-web.sh`
- `scripts/test_deploy_prod_web.sh`
- `scripts/test_deploy_prod_web_policy.py`

Adicionar somente esses nomes à allowlist operacional mantém o escopo fechado. Os testes simulam diff Git para confirmar que cada caminho é aceito e um caminho operacional parecido, mas não listado, continua recusado. Os runtimes e seus blobs aprovados permanecem intocados. A alteração não autoriza publicação: CI, inventário remoto somente-leitura e aprovação protegida continuam obrigatórios.
