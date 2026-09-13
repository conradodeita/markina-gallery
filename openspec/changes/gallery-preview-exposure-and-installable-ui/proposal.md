## Why

O fotógrafo precisa corrigir a apresentação de cada galeria sem mudar as demais. A interface monocromática dificulta distinguir seções, e ainda falta instalação como aplicativo para fotógrafo e cliente.

## What Changes

- Levar ativação e intensidade do ajuste automático para a etapa 04 e acrescentar exposição por galeria, aplicada após a correção automática.
- Reprocessar explicitamente o acervo a partir das prévias limpas, sem acumular edições ou alterar originais e reconhecimento facial.
- Substituir a configuração global do módulo anterior por configurações isoladas; preservar o estado das galerias existentes e iniciar novas desligadas.
- Dar hierarquia visual aos componentes compartilhados com a identidade solicitada pelo proprietário: preto, amarelo e tons cinza/bege, sem prejudicar a fotografia ou o layout fluido.
- Entregar manifesto, ícones, instalação contextual e aviso offline neutro, sem cache de dados privados.

## Capabilities

### New Capabilities

- `media-storage/gallery-preview-adjustment`: configuração e exposição por galeria; evolui a capacidade ainda não consolidada de `add-optional-preview-auto-adjustment`.
- `installable-app`: instalação e comportamento seguro do PWA.
- `shared-visual-hierarchy`: cores e hierarquia em componentes compartilhados.

### Modified Capabilities

Nenhuma spec consolidada tem seu contrato substituído; autorização de mídia e proteção permanecem intactas.

## Impact

Backend do módulo, migration aditiva, worker opcional, etapa 04, Configurações e estilos compartilhados; frontend PWA sem serviços externos. Presets Lightroom, edição final, cache offline de fotos, push e mudanças financeiras ficam fora do escopo. Deploy requer inventário e autorização operacional; worker deve ser atualizado junto da API.
