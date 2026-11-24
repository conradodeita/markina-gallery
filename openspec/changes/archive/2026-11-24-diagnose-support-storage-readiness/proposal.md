# Proposal

## Why

O `support-inventory` atual informa `backup_directory=directory_invalid`, mas não distingue link simbólico, tipo incompatível, owner, grupo ou modo. Sem essa distinção somente de leitura, não há evidência suficiente para decidir se uma remediação protegida específica é segura.

## What Changes

- Acrescentar ao inventário de suporte uma razão estática e allowlisted para o estado de cada diretório fixo, mantendo a categoria agregada atual.
- Incluir as razões sanitizadas na fingerprint para que qualquer decisão posterior fique vinculada ao snapshot observado.
- Manter `prepare-support` e `restore-support` bloqueados sempre que o estado agregado não for `ready` ou `creatable`.
- Não criar, alterar permissões, mover, substituir ou remover diretórios, arquivos, recibos ou cópias; qualquer remediação futura exige fluxo protegido separado.

## Capabilities

### New Capabilities

- `deployment-operations/backup-runtime-support-diagnostics`: razões sanitizadas e somente de leitura para a prontidão dos diretórios fixos de suporte do runtime de backup.

### Modified Capabilities

Nenhuma.

## Impact

Afeta o contrato de saída e fingerprint do `support-inventory` e `restore-support-inventory`, o classificador local dos diretórios de suporte, seus testes e a documentação OpenSpec. Não adiciona operação remota nem altera o protocolo de escrita, o Drive, o runtime de backup ou os gates operacionais.
