# Spec Delta

## ADDED Requirements

### Requirement: Visão Geral resume pastas com importação de fotos em andamento
O card SHALL contar pastas de conteúdo públicas ou privadas com ao menos uma foto cujo `MediaJob` esteja `queued` ou `processing`. O segundo valor SHALL somar todas as fotos cadastradas nas pastas contadas, ainda que algumas já tenham terminado de processar. Pastas auxiliares e pastas sem job de mídia ativo não entram nos valores. A interface SHALL identificar os valores como pastas com importação ativa e total de fotos dentro dessas pastas.

#### Scenario: Pasta pública e pasta privada com processamento ativo
- **WHEN** uma pasta de conteúdo pública e uma pasta de conteúdo privada possuem cada uma ao menos um job queued ou processing
- **THEN** o card conta duas pastas e soma todas as fotos cadastradas nas duas pastas

#### Scenario: Uma foto ativa entre fotos já processadas
- **WHEN** uma pasta contém três fotos e ao menos uma delas ainda tem job queued ou processing
- **THEN** a pasta conta uma vez e o detalhe soma as três fotos

#### Scenario: Todos os jobs da pasta terminaram
- **WHEN** uma pasta contém fotos, mas nenhum job está queued ou processing
- **THEN** a pasta e suas fotos não aparecem nos indicadores de importação ativa

#### Scenario: Job falhou
- **WHEN** uma pasta contém fotos, mas seu único job está failed
- **THEN** a pasta não é contada como importação em andamento

#### Scenario: Pasta de capa
- **WHEN** uma pasta auxiliar de capa possui um job queued ou processing
- **THEN** ela e suas fotos não alteram os indicadores de importação de conteúdo
