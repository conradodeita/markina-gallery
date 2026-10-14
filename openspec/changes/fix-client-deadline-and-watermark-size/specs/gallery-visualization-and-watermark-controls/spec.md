## MODIFIED Requirements

### Requirement: Configuração visual e marca-d’água

O sistema SHALL permitir ao fotógrafo configurar texto, tipografia, cor, tamanho entre 10 e 96 px e direção (horizontal, vertical ou diagonal) da marca-d’água antes de gerar novas prévias. A prova administrativa SHALL representar o tamanho escolhido em todo esse intervalo sem aplicar um teto visual menor que o aceito pelo servidor. A etapa Imagens SHALL oferecer um único comando de carregamento que abre o seletor local e envia os JPEGs escolhidos.

#### Scenario: Carregamento direto

- **WHEN** o fotógrafo clica em “Carregar fotos”
- **THEN** o seletor local é aberto e os arquivos JPEG selecionados são registrados e enviados para a pasta atual

#### Scenario: Prova acima de 32 px

- **WHEN** o fotógrafo escolhe um tamanho válido maior que 32 px
- **THEN** a prova administrativa representa o valor escolhido sem reduzi-lo artificialmente para 32 px

