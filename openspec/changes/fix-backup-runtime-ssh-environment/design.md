> **SUPERCEDIDA — NÃO IMPLEMENTAR NEM DESPACHAR.** Este plano de credenciais e operações SSH pertencia ao runtime de backup cancelado em 25/11/2026. Mantido apenas como histórico; não provisionar credenciais para esse fluxo. Consulte [retire-platform-backup-runtime](../retire-platform-backup-runtime/proposal.md) e [prove-open-source-backup-and-recovery](../prove-open-source-backup-and-recovery/proposal.md).

## Context

A API do GitHub confirmou por nomes que `production` contém `PRODUCTION_SSH_*` e que `production-preflight` contém `PRODUCTION_PREFLIGHT_SSH_*`. Os valores de host, porta e usuário coincidem entre os ambientes. Essa igualdade não identifica a chave nem prova que ela aciona o wrapper restrito.

## Decisions

1. Manter inventário inicial em `production-preflight`. O job `operate` deve usar o destino configurado em `production` e uma chave e known-hosts explicitamente vinculados ao canal restrito de backup. Confirmar a associação da credencial ao wrapper no host com inventário somente leitura pelo mesmo canal. Não usar uma chave genérica como fallback, transferir segredos por outputs ou mover a execução da etapa mutável ao ambiente de preflight.
2. Reutilizar no job protegido o mesmo canal confirmado para a leitura posterior à operação. Antes do download validar presença da configuração e igualdade do destino com o inventário. Manter CI da main exata, fingerprint, pacote, lock e aprovação existentes. Diagnósticos de ausência/divergência devem ser fixos e não imprimir valores de credenciais.
3. Tratar provisionamento como etapa separada, com autorização explícita para alterações de credenciais. A confirmação do ambiente deve preceder a tentativa mutável. Não reutilizar a autorização do run 45545034072 em outro SHA.
