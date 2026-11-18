# Design

## Context

Os helpers `scripts/deploy-prod-app-services.sh` e `scripts/deploy-prod-web.sh` mantiveram a lista de Compose do período em que o overlay RAW era instalado. A aposentadoria `8b494094d5acc393fdd25b68a4b7a3deabb55a4a` removeu `docker/docker-compose.raw-development.yml`; o SHA candidato `99885a8343b9267957941995d3e70a30f691e60a` também não contém esse arquivo. O inventário oficial falhou na checagem de presença dos overlays antes de consultar os containers.

## Goals / Non-Goals

**Goals:**

- Remover a dependência do overlay RAW aposentado no inventário e release API/web.
- Tornar mensagens de ausência de manifesto acionáveis, sem expor configuração ou segredo.
- Preservar as verificações de presença, identidade e hashes dos demais manifestos e containers.

**Non-Goals:**

- Reativar ou recriar o overlay RAW.
- Alterar qualquer serviço Compose, container, imagem, worker, proxy, banco, segredo ou dado de produção.
- Aceitar um manifesto ausente, identidade divergente ou fingerprint inválido como condição segura.

## Decisions

- Retirar `docker/docker-compose.raw-development.yml` da lista `COMPOSE_EXTRA_FILES` e de `COMPOSE_FILE_LABEL` dos helpers API/web. A prova da aposentadoria vem do commit que removeu o arquivo; não inferir a configuração remota apenas por documentação histórica.
- Manter as validações restantes de arquivo e de labels dos containers. Se um manifesto ainda exigido estiver ausente, a falha informa o caminho exato e aborta antes de build, troca de imagem ou recriação.
- Atualizar o blob permitido do helper no wrapper SSH versionado. A cópia root-owned no servidor só será atualizada pelo procedimento operacional autorizado, com conferência de proprietário, modo e hash.
- Não alterar o helper facial neste escopo. Seu fluxo tem pins, gates e inventário independentes.

## Risks / Trade-offs

- O preflight pode revelar outro overlay ausente depois da remoção da referência aposentada. Nesse caso, ele continua bloqueando antes de qualquer mutação; o inventário remoto determinará o próximo passo.
- Atualizar o pin do wrapper exige reconciliar a cópia root-owned do servidor antes de executar o novo preflight.

## Migration Plan

1. Atualizar helper, wrapper versionado, teste de regressão e documento operacional.
2. Passar os gates focados, OpenSpec estrito e CI do PR.
3. Atualizar e verificar a cópia root-owned do wrapper pelo procedimento autorizado.
4. Reexecutar o inventário remoto para o SHA integrado. Só prosseguir para o release protegido se fingerprint, manifestos, versão, schema, saúde e flag facial corresponderem ao plano aprovado.
