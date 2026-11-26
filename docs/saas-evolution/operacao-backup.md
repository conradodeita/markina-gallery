# Operação de backup e recuperação

> Guia da tentativa aposentada em 25/11/2026. Os comandos, destinos, credenciais, rotinas e passos de habilitação descritos anteriormente foram retirados e não devem ser executados.

## Direção vigente

A próxima avaliação está documentada em [prove-open-source-backup-and-recovery](../../openspec/changes/prove-open-source-backup-and-recovery/proposal.md). Ela cobre, com dados sintéticos e destinos isolados, backup global do PostgreSQL, extração seletiva de fotógrafo e recuperação de pasta fria pelo fluxo existente.

Restic e Rclone são candidatos a ferramentas comuns; Backrest pode ser avaliado como painel opcional. Nada está instalado ou autorizado para produção por essa proposta. A prova local não pode usar dados de cliente ou credenciais reais.

## Estado da higienização

A retirada de código e do runtime do host está especificada em [retire-platform-backup-runtime](../../openspec/changes/retire-platform-backup-runtime/tasks.md). Até a integração e execução do workflow protegido, considerar desconhecida a ausência dos arquivos do host e não executar SSH ad hoc, comandos systemd, Docker Compose, Drive, backup ou restauração.

A chave de navegador do Google Picker foi removida da lista ativa do projeto Cloud. O OAuth compartilhado e a cópia existente no Drive permanecem protegidos. A chave offline em D: será removida pelo proprietário.
