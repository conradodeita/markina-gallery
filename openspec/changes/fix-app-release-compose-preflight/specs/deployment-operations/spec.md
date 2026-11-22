# Spec Delta

## ADDED Requirements

### Requirement: Release API/web valida manifestos Compose vigentes

Os helpers de inventário e release API/web SHALL NOT exigir um overlay Compose removido por uma mudança de aposentadoria integrada. SHALL continuar conferindo os demais arquivos e a identidade Compose dos containers ativos. Quando um manifesto exigido estiver ausente, a falha SHALL identificar o caminho e SHALL ocorrer antes de build, troca de imagem ou recriação.

#### Scenario: Overlay RAW aposentado

- **WHEN** um helper API/web é executado após a aposentadoria do overlay RAW e o arquivo `docker/docker-compose.raw-development.yml` não existe no checkout
- **THEN** o helper API/web não o inclui na lista de manifestos nem nos labels esperados e prossegue com a conferência dos manifestos vigentes

#### Scenario: Outro manifesto ausente

- **WHEN** qualquer outro manifesto exigido pelo inventário não existe
- **THEN** o preflight falha antes de mutação e informa qual caminho está ausente

#### Scenario: Container sem healthcheck

- **WHEN** o snapshot de identidade inclui containers do projeto com e sem `State.Health`
- **THEN** a comparação preserva ID e estado de cada container, registra `none` para a saúde não configurada e não aborta por ausência desse campo

### Requirement: Overlay persistente preserva identidade dos serviços vigentes

Os helpers API/web SHALL continuar carregando todos os manifestos persistentes na ordem esperada. Um serviço aposentado definido em overlay externo sem imagem ou build MUST bloquear o inventário até reconciliação documentada, sem ser ignorado silenciosamente.

#### Scenario: Resíduo de configuração Gemma no overlay de monitoramento

- **WHEN** o overlay persistente contém a configuração de monitoramento de `face-gemma-index-worker`, sem imagem nem contexto de build, o checksum e as únicas chaves desse bloco correspondem ao inventário aprovado e não existe container Gemma em execução
- **THEN** o inventário bloqueia sem descartar o overlay nem ativar ou recriar workers aposentados

### Requirement: Reconciliação de bloco aposentado é reversível

Uma reconciliação MUST validar checksum, estrutura, proprietário/modo e runtime, guardar backup verificado antes da substituição atômica e preservar o caminho do overlay e todos os bytes externos ao bloco removido. Qualquer divergência MUST falhar sem escrita.

#### Scenario: Reconciliar bloco de monitoramento Gemma

- **WHEN** o inventário do overlay e do runtime corresponde exatamente ao plano
- **THEN** a operação guarda uma cópia modo `0600`, remove atomicamente apenas o bloco aposentado, mantém o container parado e os demais serviços/configurações, e confirma `docker compose config --quiet`
- **AND** o preflight subsequente confirma identidade e hashes API/web, schema, saúde e `FACIAL_PROCESSING_ENABLED=true` antes de permitir qualquer release

#### Scenario: Overlay ou runtime divergente

- **WHEN** o checksum, proprietário, modo, chaves do bloco ou estado do container diferem do inventário
- **THEN** nenhuma escrita ou ação Docker acontece e o deploy permanece bloqueado para novo inventário

### Requirement: Reconciliação de configuração de produção usa fluxo protegido

A operação que escreve o overlay persistente MUST estar disponível somente em `workflow_dispatch` para a branch `main`, depender dos gates completos de CI e do ambiente protegido `production`, e usar a credencial de operação desse ambiente. MUST preservar a credencial read-only do preflight e limitar a preparação Git remota à atualização de `origin/main`, sem trocar o checkout ativo.

#### Scenario: Executar reconciliação aprovada

- **WHEN** o operador dispara `app-compose-reconcile` em `main` após CI verde e o checkout remoto, `origin/main` e runtime correspondem às guardas registradas
- **THEN** o workflow transmite por stdin somente o helper versionado no SHA do run e o helper adquire o lock antes de qualquer alteração
- **AND** a operação valida o candidato Compose, guarda backup verificado, substitui atomicamente apenas o arquivo overlay e não executa ações Docker ou migration

#### Scenario: Workflow ou baseline não autorizado

- **WHEN** a execução não é manual na `main`, um gate de CI falha, o checkout remoto diverge do baseline ou o SHA de `origin/main` não coincide com o run
- **THEN** a operação não transmite o helper para mutação e mantém o runtime e o overlay intactos
