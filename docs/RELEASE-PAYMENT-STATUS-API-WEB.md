# Publicação pontual — situações financeiras em Vendas e pagamentos

Procedimento específico da change `release-payment-status-api-web`. O fluxo `deploy-prod-web.sh` continua restrito a web. Não executar `deploy-homolog.sh` nem publicar em `develop` para acionar CI de deploy.

## Alvo e impacto

- Host SSH: `ubuntu@132.145.193.169` (`clearbudget-vnic`).
- Checkout: `/opt/markina-gallery`; projeto Compose `markina-gallery`.
- Domínio: `https://markina.pickyourpic.com.br`; entrada Markina `127.0.0.1:8080`; API 8000 e web 3000 internos.
- Ambiente existente: `docker/.env.homolog`. O nome é legado; este host atende produção real. Não editar/copiar/exibir valores desse arquivo ou dos bindings.
- Base observada: `71be3b29659143293351968e15fb4886c2d72bf0`; Alembic `20261014_0081`.
- Escopo: construir e recriar API/web, com recarga do nginx **da Markina**. Banco, Redis, workers, Evolution, dados, volumes, redes, arquivos de ambiente, proxy compartilhado, DNS, certificados e outros projetos ficam fora da execução.
- Pode ocorrer breve indisponibilidade durante a troca. Builds são sequenciais; conferir memória, disco e carga antes de iniciar. Não prometer zero downtime. Se faltar capacidade, adiar a construção sem alterar os containers saudáveis.

## Inventário e aprovação

Antes da troca, apresentar ao proprietário um inventário atualizado com SHA candidato completo já integrado à main, checkout atual limpo, revisão Alembic, IDs dos containers API/web/nginx, imagens reais API/web, hashes de configuração resolvidos, domínio/porta, recursos e plano de recuperação. Aprovação de preparação não substitui aprovação desse alvo final. A execução e a eventual recuperação das imagens anteriores devem estar expressamente incluídas na aprovação.

O registro antigo `web-last-healthy.sha` não prova a imagem atual. Usar os IDs Docker observados. Baseline levantada em 2026-10-15 (reconferir):

| Serviço | Imagem anterior | Hash de configuração ativo |
| --- | --- | --- |
| API | `sha256:1efd40743c34fbf31f2b435942a4e78a8f31501928ea02ab2e238f8ba9155279` | `8c68c183a87bfdc14ea473faf7612780184934bc010d93e363c21fa39a1334a1` |
| Web | `sha256:6941be2068c9143f4a54331da2c9bac1511e8d1998b16986bfdbf631284ec560` | `ab41c5052a1fb5d1f46f676de565ddef92ad8127c6c8d2775433f3745b94ae05` |

Manter configuração resolvida somente em memória: `docker compose config --format json` pode conter segredos. Capturar sua saída e nunca imprimi-la ou gravá-la em log. Com Compose 2.35.1, o `config --hash` direto não resolve `env_file`; passar o JSON já resolvido, via stdin, a `docker compose -p markina-gallery -f - config --no-interpolate --hash api,web`. Com `APP_VERSION` da API ativa, ambos os hashes devem coincidir com os labels Docker. Não remover essa guarda para contornar divergências.

A versão da API é metadado operacional, lido exclusivamente pela chave `APP_VERSION`. No build/release usar o SHA candidato nessa variável de processo; não editar `.env`. Comparar as configurações anterior e candidata em memória: somente `services.api.environment.APP_VERSION` pode mudar.

## Manifesto fixo

Executar em `/opt/markina-gallery`, com Bash e `set -euo pipefail`. A função abaixo deve ser usada por todos os comandos Compose desta execução:

```bash
compose_release() {
  APP_VERSION="$RELEASE_VERSION" docker compose --parallel 1 \
    --env-file docker/.env.homolog -p markina-gallery \
    -f docker/docker-compose.yml \
    -f /var/lib/markina-gallery/deploy-state/branding.compose.yml \
    -f docker/docker-compose.raw-development.yml \
    -f docker/docker-compose.preview-adjustment.yml \
    -f docker/docker-compose.system-monitor.yml \
    -f /var/lib/markina-gallery/deploy-state/system-monitor.compose.yml \
    --profile facial --profile preview-adjustment "$@"
}
```

## Preparação segura

1. Após integração do PR, atualizar apenas referências com `git fetch origin main`. Não executar checkout antes da aprovação do inventário final.
2. Definir `TARGET_SHA` como o SHA completo aprovado, `PREVIOUS_SHA` como o checkout inventariado e `API_IMAGE_ID`/`WEB_IMAGE_ID` como os IDs reais aprovados. Não assumir que o SHA anterior da web em arquivo é atual.
3. Exigir árvore limpa e `git merge-base --is-ancestor "$TARGET_SHA" origin/main`. Conferir que o candidato contém `71be3b2` e o delta aprovado. O comparativo de runtime contra a produção deve mudar somente `backend/app/main.py`, a página/teste de pagamentos, `frontend/app/globals.css` e `frontend/app/ui-kit.tsx`.
4. `git diff --exit-code "$PREVIOUS_SHA" "$TARGET_SHA" -- docker backend/Dockerfile backend/requirements.txt backend/requirements-push.txt backend/migrations frontend/Dockerfile frontend/package.json frontend/package-lock.json` deve retornar zero. Conferir ausência de arquivos `.env*` ou credenciais nos contextos backend/frontend antes de construir, sem mostrar conteúdo.
5. Consultar `alembic_version` em transação SQL read-only pela API; deve ser exatamente `20261014_0081`. A migration existe na candidata. Não executar Alembic upgrade/downgrade, migrate, restore ou comandos SQL de escrita.
6. Conferir saúde, imagens, IDs e configuração contra inventário aprovado imediatamente antes da mutação. Guardar em memória os IDs dos demais containers para comparação após a execução. Divergência implica novo inventário.

## Construção e troca autorizadas

Somente depois de todos os gates e da aprovação final:

```bash
docker image tag "$API_IMAGE_ID" "markina-gallery-api:production-api-$PREVIOUS_SHA"
docker image tag "$WEB_IMAGE_ID" "markina-gallery-web:production-web-$PREVIOUS_SHA"
git switch --detach "$TARGET_SHA"
RELEASE_VERSION="$TARGET_SHA"
compose_release build api web
```

Até este ponto, API/web ativos continuam nas imagens anteriores. Conferir o build completo e recalcular as configurações; permitir somente a troca de APP_VERSION descrita acima. Capturar os IDs das novas imagens, conferir `app/main.py` do artefato novo contra o blob do SHA aprovado e conferir novamente os IDs ativos antes de trocar.

```bash
compose_release up -d --no-deps --no-build api web
docker exec markina-gallery-nginx-1 nginx -t
docker exec markina-gallery-nginx-1 nginx -s reload
```

A recarga é necessária porque `proxy_pass http://api:8000` resolve o upstream na carga de configuração. Não recriar nginx nem alterar seu arquivo. Não adicionar outros serviços ao comando, `--remove-orphans`, `down`, `prune`, migration ou mudança de ambiente.

## Verificação e registro

- Esperar API/web saudáveis, com limite de 120 segundos e consultas curtas; conferir novos IDs de imagem e `APP_VERSION` alvo.
- HTTPS `/healthz`, `/api/health`, `/` e `/admin/payments` devem retornar 200. `/api/admin/payment-communications` deve continuar negado sem sessão (403 observado). Conferir também API interna `/health` e web interna `/api/health`. A imagem do frontend é baseada em Node.js e não inclui Python; executar a verificação interna da web com Node, por exemplo: `docker exec "$WEB_CONTAINER_ID" node -e "fetch('http://127.0.0.1:3000/api/health').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"`. Reservar Python para a imagem da API.
- Conferir presença do código `confirmed_undelivered` nos artefatos publicados; não consultar dados de clientes nem inventar login. A inspeção visual autenticada exige sessão legítima disponível.
- Conferir revisão Alembic inalterada, configuração equivalente exceto APP_VERSION e que nenhum outro container foi recriado pela execução. Se outro operador mudou o ambiente, registrar e avaliar a divergência, sem tentar revertê-la.
- Ao comparar IDs de containers antes/depois, filtrar os serviços esperados pela coluna de nomes antes de comparar os demais: `grep -vE '^markina-gallery-(api|web)-1='` sobre linhas `nome=ID`. Os IDs de API e web devem mudar no release; uma comparação que os inclua acusa falsamente a troca autorizada como alteração de outro container.
- Após saúde confirmada, registrar SHAs, IDs das imagens anteriores/novas e resultados no diretório Markina `/var/lib/markina-gallery/deploy-state` e na evidência desta change. Atualizar os registros de última versão saudável API/web somente depois de concluir as verificações. Não arquivar a change antes da revisão humana.

## Recuperação autorizada

Se a construção falhar antes da troca, os containers anteriores permanecem ativos; restaurar checkout anterior limpo e tags padrão aos IDs anteriores, sem recriar serviços. Se houver falha após a troca, aplicar esta recuperação **somente se incluída na aprovação final**; caso contrário, apresentar diagnóstico e pedir aprovação.

```bash
git switch --detach "$PREVIOUS_SHA"
docker image tag "$API_IMAGE_ID" markina-gallery-api
docker image tag "$WEB_IMAGE_ID" markina-gallery-web
RELEASE_VERSION="$PREVIOUS_SHA"
compose_release up -d --no-deps --no-build api web
docker exec markina-gallery-nginx-1 nginx -t
docker exec markina-gallery-nginx-1 nginx -s reload
```

Esperar API/web saudáveis por até 120 segundos e repetir verificações de saúde interna/HTTPS, imagens e banco. Nenhuma reconstrução ou restauração de banco ocorre no rollback. Conservar as imagens novas e antigas para diagnóstico; não limpar recursos. Registrar a falha e o resultado real da recuperação.
