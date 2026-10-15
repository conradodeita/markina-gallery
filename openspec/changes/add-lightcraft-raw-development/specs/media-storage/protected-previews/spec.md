# Spec Delta

## ADDED Requirements

### Requirement: Prévia derivada de RAW sem expor a fonte

O sistema SHALL usar somente a imagem raster desenvolvida como entrada do pipeline vigente de análise e derivados e SHALL entregar exclusivamente derivados protegidos e autorizados, sem revelar RAW nem JPEG temporário em alta resolução.

#### Scenario: Prévia autorizada de foto originada em RAW
- **WHEN** cliente autorizado solicita uma foto RAW cujo processamento foi concluído
- **THEN** recebe apenas a prévia limitada, protegida e sem EXIF/GPS, pelas rotas privadas existentes

#### Scenario: Fonte temporária indisponível ou processamento incompleto
- **WHEN** a fonte está ausente, a conversão falhou ou derivados obrigatórios ainda não estão prontos
- **THEN** o sistema não serve a fonte RAW/JPEG de trabalho nem marca a foto como pronta

### Requirement: Prévia do cliente limitada para redes móveis

O sistema SHALL gerar cada JPEG final `client_preview` novo ou regenerado, incluindo o resultado de ajuste opcional e marca-d'água, com no máximo 250.000 bytes. Se a compressão até qualidade 75 não atingir o teto, o sistema SHALL reduzir as dimensões progressivamente até que o arquivo final caiba. Esse limite SHALL NOT se aplicar ao JPEG high-res temporário usado para análise facial, miniaturas ou `admin_preview`. A publicação SHALL NOT reescrever automaticamente prévias históricas.

#### Scenario: Prévia excede o limite durante a geração
- **WHEN** a prévia protegida continua acima de 250.000 bytes após a compressão JPEG até qualidade 75
- **THEN** o sistema reduz suas dimensões e repete a codificação até salvar uma prévia de no máximo 250.000 bytes

#### Scenario: Prévia histórica
- **WHEN** a change é publicada e uma foto já possui `client_preview` pronto
- **THEN** o arquivo histórico permanece intacto até uma regeneração explícita da prévia
