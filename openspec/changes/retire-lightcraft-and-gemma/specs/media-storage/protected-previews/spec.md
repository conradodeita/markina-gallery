# Spec Delta

## MODIFIED Requirements

### Requirement: Derivados locais sem metadados sensíveis

O sistema SHALL gerar e armazenar miniaturas e prévias derivadas de JPEGs no armazenamento local autorizado, sem EXIF/GPS e sem usar Google Drive como origem de entrega. O sistema SHALL NOT admitir RAW como fonte desse pipeline.

#### Scenario: Geração de prévia
- **WHEN** uma foto JPEG é preparada para uma galeria ativa
- **THEN** o sistema produz uma prévia limitada à resolução configurada e uma miniatura sem metadados sensíveis, preservando o arquivo original fora da entrega web

#### Scenario: Reprocessamento idempotente
- **WHEN** o processamento da mesma foto JPEG é repetido
- **THEN** o sistema reutiliza ou substitui somente os derivados daquela foto sem criar cópias inconsistentes

#### Scenario: Fonte RAW
- **WHEN** um arquivo RAW é apresentado como fonte para geração de prévias
- **THEN** o sistema rejeita o arquivo antes do processamento e não cria trabalho facial nem derivados
