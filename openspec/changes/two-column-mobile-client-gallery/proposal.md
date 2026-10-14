## Why

A grade fotográfica da cliente está usando apenas uma coluna em celulares, desperdiçando largura útil e tornando a navegação por muitas fotos lenta. Além disso, o texto personalizado da marca-d’água é repetido sobre a mesma foto, embora deva funcionar como uma única assinatura visual; a grade de proteção separada já está adequada e não deve ser alterada.

## What Changes

- Tornar a grade de fotos da cliente obrigatoriamente composta por duas colunas no viewport mobile.
- Usar quase toda a largura útil da tela, mantendo apenas espaçamento lateral e entre células suficiente para separar as fotos.
- Preservar a proporção de fotos horizontais e verticais, sem distorção, e manter seleção, estados, proteção e abertura no visualizador.
- Manter o comportamento fluido existente em tablet e desktop, permitindo mais colunas conforme o espaço disponível.
- Aplicar a regra às grades fotográficas públicas e privadas acessíveis à cliente, sem alterar grades ou fluxos administrativos.
- Renderizar o texto personalizado da marca-d’água exatamente uma vez por foto, respeitando a direção horizontal, diagonal ou vertical e o tamanho configurado.
- Manter a grade de proteção existente inalterada e independente do texto da marca-d’água.
- Aplicar o novo desenho somente às prévias geradas ou reprocessadas futuramente, sem reenfileirar automaticamente as fotos atualmente existentes.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-visualization-and-watermark-controls`: definir duas colunas como mínimo visual da grade fotográfica da cliente em celulares, preservar expansão responsiva nos viewports maiores e limitar o texto personalizado da marca-d’água a uma única ocorrência por foto.

## Impact

- Componentes e classes compartilhadas que renderizam grades e prévias protegidas no portal da cliente.
- Geração/renderização da camada textual da marca-d’água, sem alteração da grade de proteção.
- Testes de componentes/responsividade das galerias pública e privada e regressão dos novos derivados protegidos.
- Sem alteração de API, banco, worker, armazenamento, reconhecimento facial ou autorização.
