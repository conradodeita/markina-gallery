## ADDED Requirements

### Requirement: Configuração visual e marca-d’água

O sistema SHALL permitir ao fotógrafo configurar texto, tipografia, cor, tamanho e direção (horizontal, vertical ou diagonal) da marca-d’água antes de gerar novas prévias. A etapa Imagens SHALL oferecer um único comando de carregamento que abre o seletor local e envia os JPEGs escolhidos.

#### Scenario: Carregamento direto

- **WHEN** o fotógrafo clica em “Carregar fotos”
- **THEN** o seletor local é aberto e os arquivos JPEG selecionados são registrados e enviados para a pasta atual

### Requirement: Visualização da galeria

O sistema SHALL permitir abrir o link não listado em uma galeria autenticada e SHALL informar quando o fotógrafo estiver visualizando em modo administrativo. O fotógrafo SHALL poder configurar pastas individuais lado a lado ou sequência cronológica, com título sobre a capa conforme a configuração visual.

#### Scenario: Modo individual

- **WHEN** a galeria está configurada para pastas individuais
- **THEN** a capa é apresentada primeiro e as pastas aparecem lado a lado com nome e contagem

#### Scenario: Modo sequencial

- **WHEN** a galeria está configurada para sequência
- **THEN** a capa é apresentada primeiro e cada pasta é exibida em ordem com seu título antes das fotos

### Requirement: Exclusão em massa elegível

O sistema SHALL permitir selecionar várias fotos sem compra confirmada e excluí-las com uma única confirmação. Fotos com compra confirmada SHALL permanecer protegidas e informar o motivo do bloqueio.

#### Scenario: Exclusão parcial protegida

- **WHEN** o fotógrafo seleciona fotos elegíveis e fotos com compra confirmada
- **THEN** o sistema exclui somente as elegíveis, preserva as protegidas e informa quais não puderam ser removidas
