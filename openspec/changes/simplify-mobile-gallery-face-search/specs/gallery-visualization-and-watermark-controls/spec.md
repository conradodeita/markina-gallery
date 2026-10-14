## ADDED Requirements

### Requirement: Seleção compacta ao lado do nome da fotografia

A grade da cliente SHALL apresentar nome do arquivo e botão de seleção compactos, lado a lado em uma faixa abaixo da imagem, sem sobrepor a fotografia. SHALL preservar duas colunas no mobile, proporção integral da imagem, indicação de selecionada/comprada e separação entre ampliar e selecionar. Nomes longos SHALL caber sem rolagem horizontal, com nome completo acessível. Reduzir o tamanho visual SHALL preservar área de toque de pelo menos 44 por 44 pixels CSS sem invadir a imagem nem outros controles.

#### Scenario: Duas colunas em smartphone
- **WHEN** a cliente visualiza fotos em largura de 320, 360 ou 390 pixels CSS
- **THEN** cada foto mantém nome compacto e seleção na faixa inferior, com imagem desobstruída e sem rolagem horizontal

#### Scenario: Ações adicionais e resultados faciais
- **WHEN** uma foto possui favorito, estado comercial ou rejeição de candidata facial
- **THEN** essas ações permanecem externas à imagem, podem ocupar linha complementar e não cobrem nem deslocam nome e seleção para dentro da fotografia

#### Scenario: Seleção independente da ampliação
- **WHEN** a cliente toca na seleção ao lado do nome
- **THEN** apenas a seleção é alterada, sem abrir o visualizador; tocar na fotografia continua somente ampliando

### Requirement: Navegação ampliada sempre visível

O visualizador SHALL manter fechamento, seleção e, quando houver várias fotos, `Anterior` e `Próxima` na área útil da viewport mobile, inclusive com seleção de rostos habilitada. Seleção e navegação SHALL ocupar uma barra abaixo e fora da fotografia, sem sobreposição à imagem, inclusive durante zoom, pan ou rotação do aparelho. SHALL ajustar a área da imagem ao espaço restante e permitir rolagem de conteúdo auxiliar sem exigir rolagem para alcançar a navegação. Zoom/pan SHALL conservar geometria dos rostos e não disparar navegação ou seleção comercial acidental.

#### Scenario: Rostos habilitados em tela curta
- **WHEN** a cliente habilita rostos em viewport de 360 por 640 pixels CSS
- **THEN** fechamento e navegação permanecem visíveis, sem serem empurrados para baixo pelos controles de zoom ou pelo texto de ajuda; `Anterior`, `Próxima` e seleção ficam na barra externa, sem cobrir qualquer parte da fotografia

#### Scenario: Mudança de orientação ou altura útil
- **WHEN** a altura útil do navegador muda ou o aparelho gira
- **THEN** imagem e controles se redistribuem dentro da viewport respeitando áreas seguras, sem recortar a foto em modo ajustado
