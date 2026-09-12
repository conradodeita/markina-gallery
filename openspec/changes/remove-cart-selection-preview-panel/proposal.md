## Why

Ao abrir o carrinho, a grade principal já apresenta as fotos selecionadas, mas o resumo inferior abre simultaneamente uma segunda lista flutuante com as mesmas miniaturas. Essa duplicação encobre a galeria, reduz a área útil e confunde a revisão da cliente.

## What Changes

- Remover do resumo flutuante do carrinho o painel expansível `Revisar seleção` e sua lista duplicada de miniaturas.
- Manter as fotos selecionadas na grade principal da página do carrinho, onde continuam disponíveis para conferência, ampliação e alteração permitida.
- Preservar no resumo inferior quantidade, total, cálculo por faixas e ação de avanço para o PIX.
- Preservar o diálogo de proteção de direitos autorais, que é independente do painel removido.
- Verificar desktop e mobile para que nenhuma área lateral ou flutuante duplicada encubra as fotos.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/original-gallery-experience`: tornar a conferência do carrinho uma única superfície visual, sem repetir as fotos da grade principal em painel flutuante.

## Impact

- Página Next.js da galeria privada em modo de revisão/carrinho e seus testes de componente.
- Componente compartilhado de itens do carrinho somente se ficar sem consumidores após a remoção.
- CSS do resumo flutuante, caso existam regras exclusivas do painel removido.
- Nenhuma alteração em API, seleção persistida, preços, pedidos, pagamentos, marca-d’água ou proteção autoral.
