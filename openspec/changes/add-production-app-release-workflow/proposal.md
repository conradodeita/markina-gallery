# Proposal

## Why

O release facial protegido publica um conjunto específico de serviços e fixa blobs de runtime revisados; ele não é o caminho apropriado para alterações comerciais em API e web. A estatística precisa de um procedimento próprio que permita publicar essa atualização com inventário e aprovação exatos sem ampliar nem desativar a proteção facial.

## What Changes

- Criar um fluxo protegido e independente para inventariar e publicar somente `api` e `web` em produção.
- Exigir CI completo, SHA presente em `main`, inventário somente-leitura, configuração Compose efetiva correspondente e aprovação humana vinculada ao fingerprint do SHA e do estado observado.
- Proibir migrations, alterações de Docker/Compose, workers, banco, proxy compartilhado, segredos e serviços de terceiros neste fluxo.
- Preservar o fluxo especializado da manutenção facial e não modificar a implementação do Monitor do sistema.
- Documentar impacto potencial de reinício da API, rollback limitado a `api` e `web`, estado de wrapper SSH e pré-requisitos operacionais.

## Capabilities

### New Capabilities

### Modified Capabilities

- `deployment-operations`: adicionar contrato de release protegido, separado do procedimento facial e limitado a API/web.

## Impact

- CI do GitHub, scripts de inventário e release, wrapper SSH de preflight, política de escopo, testes e runbook de produção.
- O release pode interromper brevemente os endpoints da API e da web; o preflight deve mostrar serviços, portas, domínio, schema, SHA, rollback e possível impacto antes da aprovação.
- A publicação reinicia a API compartilhada por rotas administrativas, incluindo o Monitor, mas não altera arquivos, regras, dados ou serviços específicos do Monitor.
