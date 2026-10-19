# Design

## Decisão

Usar `package-ecosystem: docker-compose` para `/docker`. GitHub documenta esse ecossistema para Compose; o fetcher oficial do Dependabot usa o padrão `(docker-)?compose(-[\\w]+)?(?>\\.[\\w-]+)?\\.ya?ml`, que encontra o Compose base e os nomes dos overlays deste projeto.

Manter `docker` para `/backend` e `/frontend`, onde os Dockerfiles realmente residem. A correção troca apenas o tipo da entrada que falhava, sem alterar agenda, limite ou conteúdo de qualquer imagem/manifests.

## Evidências locais

O diretório contém `docker-compose.yml`, `docker-compose.local.yml`, `docker-compose.preview-adjustment.yml`, `docker-compose.raw-development.yml` e `docker-compose.system-monitor.yml`. O Compose base declara as imagens externas de runtime. O overlay RAW referencia uma imagem local criada pelo Dockerfile RAW; sua versão upstream é mantida no argumento do Dockerfile e segue coberta pelo ecossistema `docker` em `/backend`.

## Verificação

- Teste de regressão compara o conjunto de manifests encontrados com os cinco arquivos existentes e confirma `docker-compose` em `/docker` enquanto preserva as entradas Docker backend/frontend.
- A API do GitHub valida o arquivo de configuração na PR.
- Após integração, verificar a execução Dependabot imediata decorrente da configuração. Não aguardar o ciclo semanal; qualquer PR Dependabot resultante permanece sem merge.
