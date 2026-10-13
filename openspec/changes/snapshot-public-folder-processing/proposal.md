# Proposal

## Why

Pastas públicas sem configuração própria continuam lendo em tempo real os controles de prévia da galeria. Isso faz uma alteração na galeria alcançar pastas antigas e apresenta a configuração como herdada, embora o processamento deva ser independente por pasta.

## What Changes

- Ao criar uma pasta pública, iniciar o ajuste automático ligado e copiar para a configuração própria a intensidade e a exposição atuais da galeria; se não houver configuração explícita, usar 50%/0,0 EV.
- Inicializar a permissão facial da pasta pública como permitida, respeitando os gates globais e de galeria existentes.
- Isolar e ativar o ajuste em pastas públicas existentes por meio de snapshot aditivo dos valores vigentes durante a migration.
- Impedir que mudanças posteriores na configuração da galeria alterem configuração ou filas das pastas públicas já isoladas.
- Manter o contrato de pasta privada: reconhecimento facial permitido e ajuste sempre ativo em 75%/0,0 EV por padrão, independente da galeria pública.

## Capabilities

### New Capabilities

- `media-storage/public-folder-processing`: configuração independente do processamento por pasta pública.

## Impact

Endpoints de criação de pastas públicas, configuração efetiva por pasta, painel administrativo, fila do ajuste de prévias, migration aditiva e testes de contrato. A migration deriva do head `20261012_0075` e materializa snapshots para pastas públicas existentes, sem remover ou sobrescrever fotos e derivados.
