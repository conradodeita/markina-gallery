## Why

O proprietário aprovou em 11/11/2026 dar movimento discreto aos cards, preservando estabilidade dos formulários, temas e acessibilidade. A autorização “ótimo! Implemente” cobre a implementação local do padrão apresentado na conversa.

## What Changes

- Cards de navegação elevam 2 px com transição de 180 ms no mouse.
- Cards administrativos com conteúdo/formulários recebem somente destaque de borda, sem deslocamento.
- Foco de teclado visível, resposta breve ao toque e ausência de movimento não essencial quando o dispositivo pede redução de movimento.
- Aplicação inicial nas galerias/pastas de navegação e nos cards administrativos existentes; nenhuma regra de negócio muda.

## Capabilities

### Modified Capabilities
- `gallery-sales/operational-gallery-interface`: feedback visual discreto e acessível dos cards.

## Impact

CSS compartilhado apenas, sem dependência, JavaScript, chamada adicional de API ou alteração de produção. Preservar layout, áreas clicáveis, estados de publicação e cores semânticas.
