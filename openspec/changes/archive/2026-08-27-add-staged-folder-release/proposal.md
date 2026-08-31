## Why

O fotógrafo precisa concluir cada lote de fotos antes de mostrá-lo ou avisar clientes. Fotos posteriores devem formar nova pasta e nova rodada de revisão, sem alterar a percepção ou o histórico do lote anterior.

## Status

**Absorvida e supersedida em 2026-08-28.** Não implementar esta proposta como change separada. A liberação explícita de pasta/lote, a invisibilidade de itens em preparação e a nova rodada por pasta foram entregues por `launch-original-gallery-interface`. Nenhum requisito exclusivo comprovado permanece nesta proposal; ela é preservada apenas como histórico de planejamento.

## What Changes

- Modelar pastas de evento como lotes com estados de preparação e liberação explícita.
- Mostrar e comunicar uma pasta somente após o fotógrafo concluir e liberar seu conteúdo.
- Tratar fotos posteriores como nova pasta e nova rodada, visível apenas após atribuição privada e liberação.

## Capabilities

### New Capabilities

- `media-storage/staged-folder-release`: preparação, liberação e visibilidade controlada de pastas de fotos por evento.

### Modified Capabilities

- `messaging/payment-status-notifications`: comunicar a liberação de uma nova pasta somente a clientes autorizados.

## Impact

- Modelos e APIs de pastas, importação, galerias privadas e mensagens; frontend administrativo e cliente.
- Não habilita acervo coletivo público, reconhecimento facial, pagamento ou envio real de WhatsApp.
