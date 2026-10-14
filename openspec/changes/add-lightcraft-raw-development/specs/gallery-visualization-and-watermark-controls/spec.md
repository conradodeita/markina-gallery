# Spec Delta

## MODIFIED Requirements

### Requirement: Configuração visual e marca-d’água

O sistema SHALL permitir ao fotógrafo configurar texto, tipografia, cor, tamanho e direção (horizontal, vertical ou diagonal) da marca-d’água antes de gerar novas prévias. A etapa Imagens SHALL oferecer um único comando de carregamento que abre o seletor local e envia os JPEGs escolhidos ou, com o módulo RAW ativo, os arquivos RAW compatíveis para a pasta atual.

#### Scenario: Carregamento direto
- **WHEN** o fotógrafo clica em “Carregar fotos” e seleciona JPEGs
- **THEN** o seletor local é aberto e os arquivos JPEG selecionados são registrados e enviados para a pasta atual pelo fluxo JPEG vigente

#### Scenario: Carregamento RAW compatível
- **WHEN** o fotógrafo clica em “Carregar fotos”, o módulo RAW está ativo e seleciona formatos suportados
- **THEN** os RAWs são registrados e encaminhados ao desenvolvimento temporário antes de disponibilizar prévias

#### Scenario: Seletor e módulo RAW desligado
- **WHEN** o módulo RAW está desligado
- **THEN** a interface mantém o carregamento JPEG e não anuncia formatos RAW como aceitos
