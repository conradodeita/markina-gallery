## Why

O proprietário escolheu avaliar ferramentas open source para substituir a tentativa de backup global. A mesma prova deve incluir recuperação de um fotógrafo e restauração de arquivos frios solicitada pelo fotógrafo.

## What Changes

- Provar um backup PostgreSQL cifrado e sua recuperação independente em banco descartável.
- Recuperar de forma isolada os dados de um fotógrafo e uma pasta de mídia fria pelo fluxo do produto.
- Avaliar Restic e Rclone como componentes comuns, com Backrest opcional para acompanhamento operacional.

## Capabilities

### New Capabilities

- `media-storage/open-source-backup-recovery-proof` cobre a prova sintética das três recuperações.

### Modified Capabilities

As regras vigentes do Console e do arquivo de mídia orientam a prova.

## Impact

A prova usa dados sintéticos e destinos isolados. A decisão de publicar será tomada com os resultados de duração, custo operacional, isolamento e recuperação.

## Non-goals

O ensaio exclui acesso à produção, alteração de integrações reais e publicação de dados.
