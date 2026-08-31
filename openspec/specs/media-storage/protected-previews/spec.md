# media-storage/protected-previews Specification

## Purpose
Oferecer prévias privadas para galerias e compras, preservando a identificação visual necessária sem expor arquivos originais ou acervos fora da autorização.

## Requirements

### Requirement: Derivados locais sem metadados sensíveis

O sistema SHALL gerar e armazenar miniaturas e prévias derivadas no armazenamento local autorizado, sem EXIF/GPS e sem usar Google Drive como origem de entrega.

#### Scenario: Geração de prévia

- **WHEN** uma foto é preparada para uma galeria ativa
- **THEN** o sistema produz uma prévia limitada à resolução configurada e uma miniatura sem metadados sensíveis, preservando o arquivo original fora da entrega web

#### Scenario: Reprocessamento idempotente

- **WHEN** o processamento da mesma foto é repetido
- **THEN** o sistema reutiliza ou substitui somente os derivados daquela foto sem criar cópias inconsistentes

### Requirement: Entrega privada por papel

O sistema SHALL entregar prévias somente após autenticação e autorização da galeria derivada ou do papel administrativo, sem disponibilizar URL pública persistente.

#### Scenario: Prévia do cliente

- **WHEN** o cliente autorizado abre uma foto atribuída à sua galeria derivada
- **THEN** o sistema entrega somente a prévia protegida daquela foto e não revela outra foto, galeria ou original

#### Scenario: Prévia administrativa

- **WHEN** o fotógrafo autenticado abre uma foto para conferência administrativa
- **THEN** o sistema entrega uma prévia administrativa sem marca-d'água, limitada à resolução de conferência e sem fornecer download do original

#### Scenario: Acesso indevido

- **WHEN** uma sessão sem permissão solicita uma prévia por identificador ou caminho
- **THEN** o sistema nega a solicitação sem revelar se o arquivo ou a foto existem

### Requirement: Proteção visual aplicada ao conteúdo

O sistema SHALL aplicar marca-d'água e demais proteção configurada à imagem de prévia entregue ao cliente, e não somente como camada visual do navegador.

#### Scenario: Cliente visualiza prévia protegida

- **WHEN** uma prévia é entregue ao cliente
- **THEN** a imagem recebida já contém a proteção visual configurada e não inclui EXIF/GPS

#### Scenario: Ampliação autorizada

- **WHEN** cliente ou fotógrafo amplia uma prévia permitida
- **THEN** o sistema mantém a mesma autorização e o limite de resolução correspondente ao seu papel
