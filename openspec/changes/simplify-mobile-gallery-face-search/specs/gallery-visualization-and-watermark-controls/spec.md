## ADDED Requirements

### Requirement: Seleção compacta ao lado do nome da fotografia

A grade móvel SHALL mostrar nome completo/acessível e seleção em faixa compacta abaixo da imagem, sem sobreposição; conserva duas colunas, proporção da foto e estados selecionado/comprado. Ampliar e selecionar são distintos. Nomes longos não causam rolagem horizontal; alvo tem pelo menos 44×44 CSS pixels.

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

No mobile, o visualizador SHALL manter fechar, selecionar e navegar (`Anterior`/`Próxima`) visíveis em barra externa abaixo da foto, inclusive com busca facial. A imagem se ajusta ao espaço útil; não é preciso rolar para os controles. Zoom, pan e rotação preservam geometria facial sem navegação ou seleção acidental.

#### Scenario: Rostos habilitados em tela curta
- **WHEN** a cliente habilita rostos em viewport de 360 por 640 pixels CSS
- **THEN** fechamento e navegação permanecem visíveis, sem serem empurrados para baixo pelos controles de zoom ou pelo texto de ajuda; `Anterior`, `Próxima` e seleção ficam na barra externa, sem cobrir qualquer parte da fotografia

#### Scenario: Mudança de orientação ou altura útil
- **WHEN** a altura útil do navegador muda ou o aparelho gira
- **THEN** imagem e controles se redistribuem dentro da viewport respeitando áreas seguras, sem recortar a foto em modo ajustado
