> **SUPERCEDIDA — NÃO IMPLEMENTAR NEM DESPACHAR.** Este ajuste de fingerprint pertencia ao vínculo do runtime Google Picker cancelado em 25/11/2026. As tarefas abertas ficam somente como histórico; consulte [retire-platform-backup-runtime](../retire-platform-backup-runtime/proposal.md) e a direção vigente [prove-open-source-backup-and-recovery](../prove-open-source-backup-and-recovery/proposal.md).

## Why

O run 45615204063 recusou o vínculo antes de escrever porque 84 KiB de variação de espaço alteraram a fingerprint integral. A v2 permaneceu igual.

## What Changes

- Usar a fingerprint estável também em bind-and-rehearse, com capacidade revalidada sob o lock.
- Preservar a seleção recente pelo Picker, a aprovação protegida, o runtime instalado verificado e a fingerprint integral da reconciliação.

## Capabilities

### New Capabilities

- `deployment-operations/backup-bind-approval`: validação da aprovação do vínculo e ensaio sintético.

### Modified Capabilities

Nenhuma spec principal é alterada nesta etapa.

## Impact

Workflow de backup, wrapper fixo e regressões. A exceção anterior para uso da v2 apenas em install é substituída para bind-and-rehearse; reconcile permanece sujeito ao contrato integral.
