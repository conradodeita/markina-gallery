## Why

O tamanho configurado da marca-d’água é aplicado como pixels absolutos no derivado, de modo que `74` ocupa uma fração pequena de uma prévia com cerca de 1.600 pixels e encolhe ainda mais na tela. O fotógrafo precisa controlar a cobertura visual real da assinatura para proteger adequadamente as novas fotos.

## What Changes

- **BREAKING**: reinterpretar o controle numérico de tamanho, preservado entre 10 e 96, como percentual aproximado do eixo útil da foto na direção escolhida, e não como pixels absolutos do derivado.
- Calcular dinamicamente o tamanho da fonte para que, por exemplo, `74` faça a ocorrência única ocupar aproximadamente 74% do espaço útil horizontal, vertical ou diagonal correspondente.
- Conter a camada rotacionada dentro da foto, sem cortar o texto e preservando posição, cor, opacidade, tipografia e sombra.
- Fazer a prova administrativa representar a mesma escala proporcional aplicada pelo pipeline de mídia.
- Manter a grade de proteção inalterada e independente do texto único.
- Não reprocessar automaticamente prévias existentes; a nova escala valerá para derivados gerados após a publicação.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-visualization-and-watermark-controls`: definir o tamanho como cobertura proporcional da foto e alinhar prova administrativa e derivado protegido.

## Impact

- Gerador Pillow da camada textual da marca-d’água e testes de mídia nas três direções e em diferentes proporções de foto.
- Formulário e prova de proteção no frontend, mantendo o mesmo campo persistido e o intervalo 10–96.
- Nenhuma migration, reindexação facial, mudança na grade de proteção ou reprocessamento automático do acervo existente.
