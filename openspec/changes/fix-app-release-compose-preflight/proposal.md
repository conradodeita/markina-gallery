# Proposal

## Why

O preflight do release API/web falhou antes de inventariar a aplicação porque o helper ainda exige `docker/docker-compose.raw-development.yml`. A mudança `retire LightCraft RAW and Gemma` removeu esse arquivo, e ele também não existe no SHA candidato. A lista obsoleta bloqueia o inventário sem provar divergência dos containers ativos.

## What Changes

- Remover dos helpers de release API/web apenas a referência ao overlay RAW aposentado.
- Incluir o caminho do manifesto ausente nas mensagens de falha para permitir diagnóstico preciso, mantendo o bloqueio fechado.
- Atualizar o pin do helper de inventário no wrapper SSH versionado e as regressões/documentação correspondentes.
- Reconciliar, com backup e guarda por checksum, a declaração de serviço Gemma aposentado encontrada no overlay persistente de monitoramento do host; preservar o caminho do overlay e as demais configurações.
- Executar essa escrita somente por uma operação de workflow_dispatch dedicada, após CI verde e aprovação do ambiente protegido `production`, sem ampliar a chave read-only do preflight.
- Reexecutar o preflight somente-leitura; qualquer outro manifesto ausente ou divergência de identidade continua bloqueando o deploy.

## Capabilities

### New Capabilities

### Modified Capabilities

- `deployment-operations`: reconciliar os manifestos exigidos pelo preflight API/web com os overlays ainda versionados após a aposentadoria do RAW.

## Impact

Scripts, testes, documentação de operação e uma reconciliação estritamente delimitada de estado Compose persistente. A reconciliação remove apenas a entrada de configuração do worker Gemma aposentado, sem recriar serviço, container, imagem ou volume. Não altera o `.env`, secrets, banco, dados, serviços ativos, configuração facial nem workers. O inventário continua somente-leitura e a publicação permanece limitada a `api` e `web`.
