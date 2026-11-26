## Why

O proprietário encerrou a tentativa de lançar a rotina própria de backup global após o ensaio do Drive falhar. A interface ainda apresenta a escolha de pasta da rotina descontinuada. A retirada também precisa alcançar os recursos, credenciais e cópias exclusivos dessa tentativa.

## What Changes

- Retirar da interface e da API o fluxo de autorização de pasta do backup global.
- Desativar os workflows exclusivos da tentativa e retirar o canal de credenciais exclusivo do backup.
- Inventariar e retirar os componentes instalados, credenciais dedicadas e cópias comprovadamente pertencentes à tentativa.

## Capabilities

### New Capabilities

- `deployment-operations/platform-backup-retirement` define a retirada da implementação descontinuada.

### Modified Capabilities

Nenhuma capability consolidada requer alteração nesta etapa.

## Impact

A retirada afeta o seletor do Console, as rotas do Picker e os componentes de operação do backup global. O contrato de integração Drive, o arquivo de mídia, os mecanismos de rollback da aplicação e a operação dos clientes permanecem protegidos.

## Non-goals

A futura implementação open source de backup global e por fotógrafo tem escopo próprio.
