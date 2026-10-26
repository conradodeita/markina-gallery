# Spec Delta

## MODIFIED Requirements

### Requirement: Configuração visual e marca-d’água

O sistema SHALL permitir ao fotógrafo configurar texto, tipografia, cor, tamanho e direção (horizontal, vertical ou diagonal) da marca-d’água antes de gerar novas prévias. A etapa Imagens SHALL oferecer um único comando de carregamento que abre o seletor local e envia somente os JPEGs escolhidos.

#### Scenario: Carregamento direto
- **WHEN** o fotógrafo clica em “Carregar fotos”
- **THEN** o seletor local é aberto e os JPEGs selecionados são registrados e enviados para a pasta atual

#### Scenario: Arquivo RAW selecionado
- **WHEN** o fotógrafo seleciona um arquivo RAW na etapa Imagens
- **THEN** o sistema rejeita o arquivo antes de registrá-lo e orienta o fotógrafo a enviar um JPEG
