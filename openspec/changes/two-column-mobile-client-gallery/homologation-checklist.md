# Roteiro de homologação visual

## Grade da cliente

Validar tanto uma Galeria pública autorizada quanto a galeria privada correspondente:

1. Em viewport de `320 px`, confirmar duas fotos por linha, gap compacto, ausência de rolagem horizontal e controles acionáveis.
2. Repetir em `360 px` e `390 px`.
3. Confirmar que fotos verticais e horizontais preservam a proporção e não são recortadas nem distorcidas.
4. Abrir uma foto no visualizador, navegar para a próxima e fechar.
5. Selecionar e desmarcar uma foto e confirmar que o contador continua correto.
6. Se houver resultados faciais, confirmar que os blocos de melhores/outros resultados usam a mesma grade de duas colunas.
7. Em tablet e desktop, confirmar que a grade expande para mais colunas e usa a largura disponível.

## Marca-d’água em novas prévias

O acervo existente em homologação é somente de teste e SHALL NOT ser reenfileirado nesta entrega.

1. Depois do deploy, carregar uma nova foto de teste ou aguardar uma nova prévia ser gerada pelo fluxo normal.
2. Confirmar que o texto personalizado aparece exatamente uma vez na foto.
3. Confirmar que direção, tamanho, posição, cor, opacidade e sombra correspondem à configuração vigente.
4. Confirmar que a grade de proteção continua presente e visualmente inalterada quando habilitada.
5. Não salvar novamente a configuração de proteção apenas para este teste, pois o endpoint vigente reenfileira as prévias existentes.

As direções horizontal, diagonal e vertical e os tamanhos mínimo/máximo possuem cobertura automatizada. A revisão humana pode usar a configuração vigente e uma nova prévia representativa.

## Aceite

A change permanece sem sincronização/arquivamento até o proprietário confirmar a revisão visual no aparelho real.
