# Spec Delta

## MODIFIED Requirements

### Requirement: Pasta preparada antes da liberação

O sistema SHALL manter cada pasta de um acervo em estado de preparação até que o fotógrafo conclua seu conteúdo e a libere explicitamente. Fotos JPEG em preparação e RAWs em conversão SHALL permanecer exclusivas da área administrativa. Uma pasta SHALL NOT ser liberada enquanto houver conversão ou derivados obrigatórios pendentes.

#### Scenario: Upload em andamento
- **WHEN** o fotógrafo adiciona JPEGs a uma pasta ainda em preparação
- **THEN** ele vê progresso, sucesso ou falha de cada arquivo e nenhuma cliente vê a pasta ou suas fotos

#### Scenario: Conversão RAW em andamento
- **WHEN** o fotógrafo adiciona RAWs a uma pasta ainda em preparação
- **THEN** ele vê progresso, sucesso ou falha por arquivo e nenhuma cliente vê fotos dessa pasta antes de a conversão e os derivados obrigatórios terminarem

#### Scenario: Falha individual de conversão
- **WHEN** a conversão de um RAW falha dentro de uma pasta em preparação
- **THEN** a falha fica visível ao fotógrafo, a foto não é publicada e o restante da pasta permanece isolado até liberação explícita
