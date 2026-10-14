## MODIFIED Requirements

### Requirement: Configuração visual e marca-d’água

O sistema SHALL permitir ao fotógrafo configurar texto, tipografia, cor, tamanho e direção (horizontal, vertical ou diagonal) da marca-d’água antes de gerar novas prévias. O texto personalizado SHALL aparecer exatamente uma vez por foto protegida, respeitando a direção e o tamanho configurados, enquanto a grade de proteção SHALL permanecer uma camada independente. A etapa Imagens SHALL oferecer um único comando de carregamento que abre o seletor local e envia os JPEGs escolhidos.

#### Scenario: Carregamento direto

- **WHEN** o fotógrafo clica em “Carregar fotos”
- **THEN** o seletor local é aberto e os arquivos JPEG selecionados são registrados e enviados para a pasta atual

#### Scenario: Texto único em qualquer direção

- **WHEN** uma prévia protegida é gerada com texto personalizado nas direções horizontal, diagonal ou vertical
- **THEN** o texto aparece uma única vez na foto, com a direção e o tamanho configurados, sem repetição ou mosaico

#### Scenario: Grade de proteção preservada

- **WHEN** o fotógrafo mantém a grade de proteção habilitada junto com o texto personalizado
- **THEN** a grade continua sendo aplicada conforme sua configuração vigente sem multiplicar o texto da marca-d’água

### Requirement: Visualização da galeria

O sistema SHALL permitir abrir o link não listado em uma galeria autenticada e SHALL informar quando o fotógrafo estiver visualizando em modo administrativo. O fotógrafo SHALL poder configurar pastas individuais lado a lado ou sequência cronológica, com título sobre a capa conforme a configuração visual. Nas grades fotográficas acessíveis à cliente, o sistema SHALL apresentar duas colunas desde o viewport mobile e SHALL expandir responsivamente a quantidade de colunas em telas maiores, usando a largura útil sem distorcer as fotos.

#### Scenario: Modo individual

- **WHEN** a galeria está configurada para pastas individuais
- **THEN** a capa é apresentada primeiro e as pastas aparecem lado a lado com nome e contagem

#### Scenario: Modo sequencial

- **WHEN** a galeria está configurada para sequência
- **THEN** a capa é apresentada primeiro e cada pasta é exibida em ordem com seu título antes das fotos

#### Scenario: Grade fotográfica no celular

- **WHEN** a cliente abre uma grade de fotos autorizada em um viewport mobile
- **THEN** as fotos aparecem em duas colunas que ocupam a largura útil da tela, com espaçamento compacto e sem rolagem horizontal

#### Scenario: Proporções e interação preservadas

- **WHEN** a grade de duas colunas contém fotos horizontais e verticais
- **THEN** cada foto preserva sua proporção sem distorção e mantém seleção, estados, proteção e abertura no visualizador

#### Scenario: Expansão para telas maiores

- **WHEN** a cliente abre a mesma grade em tablet ou desktop
- **THEN** a quantidade de colunas aumenta conforme o espaço disponível sem restaurar uma coluna única nem criar grandes áreas laterais vazias
