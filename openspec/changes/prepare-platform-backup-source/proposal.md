> Tentativa descontinuada por decisão do proprietário em 25/11/2026. A retirada está em [retire-platform-backup-runtime](../retire-platform-backup-runtime/proposal.md).

## Why

O run 45656452636 atestou o runtime e passou a fingerprint estável, mas o vínculo parou com `unsafe` antes da escrita. O runtime esperava a ordem dos campos do systemd, enquanto a resposta real veio em outra ordem. A inspeção somente leitura confirmou que falta a configuração da origem, que a API ativa usa uma geração Compose e que os diretórios de estado do primeiro backup ainda não existem. A API em produção e o PostgreSQL alvo responderam à mesma consulta de identidade em transações somente leitura.

## What Changes

- Ler propriedades nomeadas do systemd na checagem de inércia.
- Preparar a configuração protegida da origem em operação fixa do workflow existente, com o destino desativado e sem cópia de dados. Usar a API do inventário ativo e provar que a conexão da API e o banco fixo observam o mesmo banco, versão, identidade física e schema.
- Usar ID, imagem e labels de serviço e projeto ao reatestar a API no runtime. Preservar a verificação da origem PostgreSQL.
- Inicializar sob o diretório de estado já definido pelo serviço os subdiretórios fixos de registros e artefatos quando uma execução real vier a ser autorizada.
- Manter as mudanças exclusivas ao runtime de backup fora da publicação API/web. Reaproveitar a sequência de aprovação existente.

## Capabilities

### New Capabilities

- `deployment-operations/backup-source-readiness`: prepara e atesta a origem do backup inerte.

### Modified Capabilities

Nenhuma spec principal é alterada nesta etapa.

## Impact

Workflow, wrapper fixo, runtime de backup e testes. Nenhuma mudança de schema, porta, credencial, destino Drive ou rotina de terceiros. A primeira cópia real e o timer continuam sujeitos às aprovações existentes.
