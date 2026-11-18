# Design

## Context

Os helpers `scripts/deploy-prod-app-services.sh` e `scripts/deploy-prod-web.sh` mantiveram a lista de Compose do período em que o overlay RAW era instalado. A aposentadoria `8b494094d5acc393fdd25b68a4b7a3deabb55a4a` removeu `docker/docker-compose.raw-development.yml`; o SHA candidato `99885a8343b9267957941995d3e70a30f691e60a` também não contém esse arquivo. O inventário oficial falhou na checagem de presença dos overlays antes de consultar os containers.

Após a integração da correção, o run de CI `44247817045`, attempt 2, passou nos gates de código e falhou somente no preflight Compose: `face-gemma-index-worker` não tem imagem nem contexto de build. A definição não está nos manifestos versionados; ela está no arquivo externo `/var/lib/markina-gallery/deploy-state/system-monitor.compose.yml`, com proprietário `ubuntu:ubuntu`, modo `0600`, tamanho de 653 bytes e SHA-256 `c63599b84764f6141cf9860ce1a352f6e11eae55ea4c24b75959ca277c3cd60e`. A inspeção sem valores confirmou que o bloco desse serviço contém somente `environment.SYSTEM_MONITOR_ENABLED`, sem `image` ou `build`. A consulta Docker somente-leitura observou zero containers Gemma em execução e um container Gemma em todos os estados; o container parado será preservado.

## Goals / Non-Goals

**Goals:**

- Remover a dependência do overlay RAW aposentado no inventário e release API/web.
- Tornar mensagens de ausência de manifesto acionáveis, sem expor configuração ou segredo.
- Preservar as verificações de presença, identidade e hashes dos demais manifestos e containers.
- Remover somente a configuração remanescente do worker Gemma aposentado do overlay persistente, com cópia de recuperação verificada e sem alterar containers.

**Non-Goals:**

- Reativar ou recriar o overlay RAW.
- Remover, iniciar ou recriar container/imagem/volume, incluindo o container Gemma parado preservado no host.
- Alterar qualquer serviço ativo, worker ativo, proxy, banco, segredo, dado, `.env`, `APP_ENV` ou `FACIAL_PROCESSING_ENABLED` de produção.
- Aceitar um manifesto ausente, identidade divergente ou fingerprint inválido como condição segura.

## Decisions

- Retirar `docker/docker-compose.raw-development.yml` da lista `COMPOSE_EXTRA_FILES` e de `COMPOSE_FILE_LABEL` dos helpers API/web. A prova da aposentadoria vem do commit que removeu o arquivo; não inferir a configuração remota apenas por documentação histórica.
- Manter as validações restantes de arquivo e de labels dos containers. Se um manifesto ainda exigido estiver ausente, a falha informa o caminho exato e aborta antes de build, troca de imagem ou recriação.
- Obter o estado dos containers como JSON e tratar `State.Health` ausente como `none`; o template Go anterior falhava quando o mapa `Health` não existia, embora esses containers fossem válidos e precisassem permanecer na comparação. A falha deve continuar fechada se o JSON ou o status do container forem inválidos.
- Atualizar o blob permitido do helper no wrapper SSH versionado. A cópia root-owned no servidor só será atualizada pelo procedimento operacional autorizado, com conferência de proprietário, modo e hash.
- Não alterar o helper facial neste escopo. Seu fluxo tem pins, gates e inventário independentes.
- A correção de estado exige que o overlay ainda tenha o SHA-256 registrado acima, proprietário/modo esperados, uma única entrada `face-gemma-index-worker` com as únicas chaves estruturais `environment` e `SYSTEM_MONITOR_ENABLED`, zero containers Gemma em execução e o container parado preservado. Qualquer diferença aborta sem escrita.
- Criar backup exclusivo modo `0600` no diretório de estado do projeto; validar o modelo Compose candidato antes de substituição atômica, manter proprietário/modo originais e validar novamente depois. Se a validação posterior falhar, restaurar o backup e confirmar o hash original.
- Manter todos os `-f` do Compose e a flag de perfil do helper; o caminho gravado nos labels dos containers permanece idêntico. O preflight remoto verificará novamente hashes de API/web e `FACIAL_PROCESSING_ENABLED=true` antes de qualquer release.
- Disponibilizar a escrita apenas como operação manual `app-compose-reconcile` na `main`, dependente dos gates de CI e do ambiente protegido `production`. A operação usa a credencial mutável de release e envia por stdin somente o helper versionado no SHA do workflow. A credencial e o wrapper read-only do preflight não são ampliados.
- O helper adquire o lock operacional antes de qualquer preparação Git, exige checkout limpo no baseline `bfe511f850224823254b0fc9f51fa7ff60ecfba0`, verifica o SHA remoto e busca somente `refs/heads/main`, sem trocar o `HEAD`. Depois confere a referência local, runtime e checksum antes de escrever.

## Risks / Trade-offs

- O preflight pode revelar outro overlay ausente depois da remoção da referência aposentada. Nesse caso, ele continua bloqueando antes de qualquer mutação; o inventário remoto determinará o próximo passo.
- Se o overlay externo tiver mudado, se o bloco tiver outras chaves ou se houver um worker Gemma em execução, a reconciliação não será aplicada; o deploy continua bloqueado para novo diagnóstico.
- Se o checkout remoto, sua árvore de trabalho ou o SHA de `main` divergirem antes da operação manual, o helper falha antes de escrever e não modifica serviços.
- Atualizar o pin do wrapper exige reconciliar a cópia root-owned do servidor antes de executar o novo preflight.

## Migration Plan

1. Atualizar helper, wrapper versionado, teste de regressão e documento operacional.
2. Passar os gates focados, OpenSpec estrito e CI do PR.
3. Atualizar e verificar a cópia root-owned do wrapper pelo procedimento autorizado.
4. Após integrar o change, executar `app-compose-reconcile` pelo workflow manual protegido, conferindo o SHA de `main` e o baseline antes da reconciliação.
5. Reexecutar o inventário remoto para o SHA integrado. Só prosseguir para o release protegido se fingerprint, manifestos, versão, schema, saúde e flag facial corresponderem ao plano aprovado.
