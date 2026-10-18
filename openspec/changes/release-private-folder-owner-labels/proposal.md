# Proposal

## Why

A correção para identificar responsáveis pelas pastas privadas está aprovada e validada em uma PR baseada em `develop`, mas o release protegido exige um candidato em `main`. O gate atual também fixa um conjunto antigo de arquivos e o schema `20261016_0082`, enquanto o inventário disponível registra produção no SHA `b4f15abd6a71585082758062feba7fcfcc225587` e no schema `20261017_0084`; sem reconciliar essas referências, o release falha fechado.

## What Changes

- Reconciliar a linha de produção com o último SHA já observado no servidor antes de classificar o delta que será publicado, sem disparar release durante a sincronização do histórico já ativo.
- Ampliar o gate app somente para os arquivos exatos de API e web da identificação de responsáveis, com blobs aprovados e testes/documentação associados.
- Fixar e verificar o schema observado `20261017_0084`; continuar recusando migrations no delta candidato e não executar Alembic.
- Manter o release limitado a `api` e `web`, com aprovação vinculada ao inventário/fingerprint, sem recriar worker OTP, workers faciais, banco, Redis ou Nginx.
- Registrar que o wrapper root-owned de SSH precisa aceitar o comando de inventário restrito antes do preflight; a change não altera o servidor nem contorna esse controle.

## Capabilities

### New Capabilities

### Modified Capabilities

- `deployment-operations`: reconciliar a base de comparação com o runtime implantado e permitir release comercial API/web apenas quando o delta, schema, inventário e fingerprint forem compatíveis.

## Impact

Afeta o classificador de release, workflow GitHub Actions, verificadores/manifests do release API/web, script de deploy, wrapper restrito versionado, testes e runbooks. A publicação posterior poderá causar breve interrupção da API e do web; exige preflight atualizado e aprovação específica do inventário. Nenhum worker OTP será incluído no comando de release.
