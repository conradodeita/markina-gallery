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

O sistema SHALL entregar prévias somente após autenticação e autorização da galeria e da pasta para a cliente, por compra confirmada da própria cliente ou pelo papel administrativo. Nenhuma URL persistente de prévia SHALL conceder acesso por posse ou ignorar essas condições.

#### Scenario: Prévia do cliente

- **WHEN** a cliente autorizada abre uma foto de pasta comum ou atribuída a ela
- **THEN** o sistema entrega somente a prévia protegida daquela foto, sem revelar foto, galeria ou original de terceiros

#### Scenario: Prévia administrativa

- **WHEN** o fotógrafo autenticado abre uma foto para conferência
- **THEN** o sistema entrega prévia administrativa sem marca-d'água, limitada à resolução de conferência, sem download do original

#### Scenario: Acesso indevido

- **WHEN** uma sessão sem atribuição solicita uma prévia de pasta restrita por identificador ou caminho
- **THEN** o sistema nega a solicitação sem revelar a existência da foto, mesmo quando a sessão pode ver outras pastas da mesma galeria

#### Scenario: Prévia de compra confirmada após revogação da pasta

- **WHEN** uma cliente acessa o item do próprio pedido canônico confirmado após perder a atribuição à pasta
- **THEN** o sistema entrega a prévia protegida desse item, mas nega a prévia operacional da pasta e nega o item a outra cliente ou a pedido não confirmado

### Requirement: Proteção visual aplicada ao conteúdo

O sistema SHALL aplicar marca-d'água e demais proteção configurada à imagem de prévia entregue ao cliente, e não somente como camada visual do navegador.

#### Scenario: Cliente visualiza prévia protegida

- **WHEN** uma prévia é entregue ao cliente
- **THEN** a imagem recebida já contém a proteção visual configurada e não inclui EXIF/GPS

#### Scenario: Ampliação autorizada

- **WHEN** cliente ou fotógrafo amplia uma prévia permitida
- **THEN** o sistema mantém a mesma autorização e o limite de resolução correspondente ao seu papel
