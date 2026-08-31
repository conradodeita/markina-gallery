## Why

Galerias, histórico de compras e conferência administrativa precisam mostrar imagens sem expor originais, acervo coletivo ou URLs públicas. O fotógrafo precisa identificar fotos compradas com clareza, enquanto o cliente só pode acessar prévias protegidas da sua própria galeria.

## What Changes

- Criar geração e armazenamento local de miniaturas e prévias derivadas, sem EXIF/GPS e sem servir imagens pelo Google Drive.
- Servir mídia apenas por endpoints autenticados e autorizados pela galeria derivada, nunca por URL pública persistente.
- Aplicar proteção visual na imagem destinada ao cliente; permitir ao fotógrafo prévia administrativa sem marca-d'água para conferência, sem fornecer o original.
- Adicionar visualizador com ampliação, estados de indisponibilidade e auditoria de acesso à mídia.

## Capabilities

### New Capabilities

- `media-storage/protected-previews`: geração, armazenamento e entrega autorizada de prévias e miniaturas privadas por papel.

### Modified Capabilities

<!-- Nenhuma especificação principal existente cobre prévias protegidas. -->

## Impact

- Backend FastAPI, processamento de imagem, metadados de mídia e volume local dedicado.
- Worker/fila para geração idempotente de derivados e limpeza controlada.
- Frontend de galeria, histórico e administração com visualizador protegido.
- Configuração operacional de capacidade e paths sem afetar outros projetos do servidor.
