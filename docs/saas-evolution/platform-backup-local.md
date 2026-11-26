# Backup global — registro local da tentativa encerrada

> Atualizado em 25/11/2026. O pacote backend platform_backup, seus testes, instalador, artefato, unidades systemd e integrações operacionais foram retirados do branch de higienização. Este documento substitui as instruções locais antigas, que se referiam a arquivos removidos.

## Plano vigente

A change [prove-open-source-backup-and-recovery](../../openspec/changes/prove-open-source-backup-and-recovery/proposal.md) define uma prova sintética de backup global PostgreSQL, extração de fotógrafo e recuperação de pasta fria com o mesmo conjunto open source. O código de recuperação de mídia e o fluxo de prazo/créditos permanecem ativos.

## Limites

- Não reinstalar o pacote antigo, não usar o Google Picker, não restaurar as antigas chaves/configurações e não despachar workflows retirados.
- A mudança de plano não autoriza acesso à produção, dados reais, alteração de banco, deploy, escrita no Drive ou timer.
- Identidades, raízes, chaves, namespaces e retenção do backup global, da extração de fotógrafo e do arquivo frio permanecem separados.
- A limpeza do host depende da change [retire-platform-backup-runtime](../../openspec/changes/retire-platform-backup-runtime/tasks.md) e do workflow protegido nela definido.
