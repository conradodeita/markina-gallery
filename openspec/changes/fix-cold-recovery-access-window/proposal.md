# Proposal

## Why

Em 27/11/2026 o proprietário aprovou simplificar o desbloqueio do arquivo frio. O fotógrafo escolhe o prazo inicial da pasta e recebe 30 dias fixos quando a recuperação fria é concluída. O andamento precisa ficar visível enquanto o destino devolve os arquivos.

## What Changes

- Fixar 30 dias para novos pedidos de recuperação fria do fotógrafo, contados da disponibilização íntegra. Preservar os prazos dos pedidos já aceitos e o prazo na retentativa do mesmo pedido.
- Mostrar uma barra de progresso alimentada pelo worker, com estado de fila, verificação, finalização e conclusão, sem estimativa de tempo.
- Manter taxa por pasta e ciclo, reserva prévia e débito único somente após verificação integral e disponibilização da pasta.

## Capabilities

### New Capabilities

- `media-storage/fixed-cold-recovery-access-window`: prazo fixo e acompanhamento de novas recuperações.

## Impact

Altera API, worker e painel de créditos existentes. Reutiliza o catálogo e os checkpoints, elimina o seletor de prazo e preserva contratos de encerramento de conta, expiração inicial e janela anterior ao arquivamento.

## Non-goals

- Alterar destino, provedor, tamanho da fila, retenção ou prazo inicial de acesso.
- Alterar os termos já aceitos, migrar registros históricos ou prometer duração da transferência.
