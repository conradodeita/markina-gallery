## Why

O código de carregamento progressivo da galeria está validado localmente, mas o servidor que atende clientes reais usa um checkout e uma configuração rotulados como homologação. O fluxo automatizado disponível foi feito para homologação e pode alterar serviços e configurações além do frontend, então precisamos de um procedimento de produção delimitado antes de publicar essa melhoria.

## What Changes

- Definir um fluxo de release em produção que publique somente o serviço `web` a partir de um commit aprovado de `main`.
- Exigir inventário e conferência somente-leitura do checkout, do serviço ativo e do arquivo de ambiente efetivamente montado antes de qualquer alteração.
- Restringir atualização e rollback à imagem/contêiner `web`, preservando API, workers, banco, Redis, nginx, proxy compartilhado, dados e configuração atual.
- Documentar verificações de saúde e smoke tests do domínio real, além dos limites de disponibilidade durante a recriação do serviço.
- Manter o deploy de homologação existente sem alterações e impedir que ele seja usado como atalho para produção.

## Capabilities

### New Capabilities

### Modified Capabilities
- `deployment-operations`: acrescenta contrato para release e rollback de produção limitados ao serviço web, com gates de inventário, validação e aprovação operacional.

## Impact

- Documentação e automação operacional de deploy no repositório, sob `scripts/` e/ou `docs/`.
- Serviço web Next.js do Compose `markina-gallery` no host de produção, no subdomínio `markina.pickyourpic.com.br`.
- O procedimento não altera APIs, banco de dados, migrations, workers, serviços de processamento facial, arquivo de ambiente, volumes ou recursos compartilhados.
- Esta proposta prepara um procedimento revisável. Não autoriza execução em produção; uma execução dependerá de aprovação explícita após apresentação do inventário, portas/subdomínio e plano de impacto.
