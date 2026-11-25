> **SUPERCEDIDA — NÃO IMPLEMENTAR NEM DESPACHAR.** O canal SSH era exclusivo do runtime de backup global Google/Picker cancelado em 25/11/2026. As tarefas abertas ficam somente como histórico. A retirada está em [retire-platform-backup-runtime](../retire-platform-backup-runtime/proposal.md); a direção vigente é [prove-open-source-backup-and-recovery](../prove-open-source-backup-and-recovery/proposal.md).

## Why

O run 45545034072 confirmou CI, fingerprint v2 e hash do pacote, mas abortou antes do envio porque o job em `production` recebeu variáveis SSH vazias. As referências do job apontam para nomes disponíveis somente em `production-preflight`.

## What Changes

- Separar explicitamente a configuração SSH do inventário da configuração dos comandos de backup no ambiente protegido.
- Exigir uma credencial confirmada para o wrapper restrito no job de operação. Recusar configuração ausente antes do download e emitir somente códigos de diagnóstico fixos.
- Preservar a comparação de destino, as fingerprints por operação, os gates de aprovação e a lista de comandos.

## Capabilities

### New Capabilities

- `deployment-operations/backup-runtime-ssh-environment`: contrato do canal SSH do workflow protegido de backup.

### Modified Capabilities

Nenhuma.

## Impact

Workflow do runtime de backup, testes de política e configuração protegida a provisionar separadamente. O run que falhou não transferiu o pacote nem iniciou SSH no job de operação.
