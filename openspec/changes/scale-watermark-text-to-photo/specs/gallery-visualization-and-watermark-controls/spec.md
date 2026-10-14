## MODIFIED Requirements

### Requirement: Configuração visual e marca-d’água

O sistema SHALL permitir ao fotógrafo configurar texto, tipografia, cor, tamanho entre 10 e 96 e direção horizontal, vertical ou diagonal da marca-d’água antes de gerar novas prévias. O tamanho SHALL representar a porcentagem aproximada do eixo útil da foto correspondente à direção, em vez de pixels absolutos do derivado; a camada SHALL crescer proporcionalmente às dimensões da imagem e SHALL ser contida para não cortar o texto. A prova administrativa SHALL representar a mesma cobertura aplicada pelo servidor. O texto personalizado SHALL aparecer exatamente uma vez por foto protegida, enquanto a grade de proteção SHALL permanecer uma camada independente. A etapa Imagens SHALL oferecer um único comando de carregamento que abre o seletor local e envia os JPEGs escolhidos.

#### Scenario: Carregamento direto

- **WHEN** o fotógrafo clica em “Carregar fotos”
- **THEN** o seletor local é aberto e os arquivos JPEG selecionados são registrados e enviados para a pasta atual

#### Scenario: Cobertura proporcional configurada

- **WHEN** uma nova prévia é gerada com tamanho `74`
- **THEN** a ocorrência textual ocupa aproximadamente 74% do eixo útil associado à direção escolhida, salvo redução mínima necessária para permanecer inteira dentro da foto

#### Scenario: Proporções diferentes de foto

- **WHEN** o mesmo tamanho é aplicado a fotos horizontais, verticais ou quadradas
- **THEN** a cobertura percebida permanece proporcional à respectiva foto sem usar o mesmo número de pixels absolutos para todas

#### Scenario: Texto único em qualquer direção

- **WHEN** uma prévia protegida é gerada nas direções horizontal, diagonal ou vertical
- **THEN** o texto aparece uma única vez, com a direção, cobertura e posição configuradas, sem repetição ou mosaico

#### Scenario: Texto permanece integral

- **WHEN** a cobertura solicitada se aproxima do limite da foto ou o texto é longo
- **THEN** o sistema preserva margens mínimas e reduz somente o necessário para impedir corte da camada rotacionada

#### Scenario: Prova administrativa equivalente

- **WHEN** o fotógrafo altera o tamanho na configuração de proteção
- **THEN** a prova representa proporcionalmente a cobertura que será incorporada às novas prévias

#### Scenario: Grade de proteção preservada

- **WHEN** o fotógrafo mantém a grade de proteção habilitada junto com o texto personalizado
- **THEN** a grade continua sendo aplicada conforme sua configuração vigente sem depender da escala nem multiplicar o texto
