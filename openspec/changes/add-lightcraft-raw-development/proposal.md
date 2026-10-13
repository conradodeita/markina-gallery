# Proposal

## Why

Após eventos, o fotógrafo pode precisar disponibilizar fotos antes de conseguir exportar JPEGs. O sistema pode receber RAWs, desenvolver prévias automaticamente e encaminhá-las ao pipeline já validado, desde que não retenha os arquivos-fonte e permita comparar motores e versões antes de recomendar um padrão.

## What Changes

- Permitir, de forma opt-in, o envio de RAWs para capas e pastas de conteúdo; o fluxo JPEG atual permanece inalterado e continua sendo o padrão.
- Criar um módulo de desenvolvimento RAW com seleção administrativa entre os motores suportados, incluindo LightCraft e o RawTherapee existente quando compatível.
- Vincular configurações, jobs e proveniência RAW ao tenant autenticado, preservando isolamento da galeria e da fila entre fotógrafos.
- Encaminhar o JPEG de trabalho temporário ao pipeline atual de análise facial e derivados; descartar RAW e JPEG de alta resolução após conclusão, com prazo limitado para retentativas e sem backup dos arquivos-fonte.
- Limitar cada JPEG final de prévia do cliente a 250 KB, reduzindo a resolução somente quando as tentativas de qualidade JPEG não forem suficientes para o teto.
- Exibir versão instalada, versão estável mais recente conhecida e atualização disponível, com link para notas de versão. A atualização do motor será fixada e instalada pelo procedimento controlado de publicação; o sistema não substituirá binários automaticamente.
- Comparar qualidade, compatibilidade de formatos/câmeras, tempo e consumo nos recursos ARM previstos antes de recomendar LightCraft como padrão. Falhas de conversão não liberarão mídia parcial nem afetarão o fluxo JPEG.

O proprietário autorizou em 13/10/2026 commit, push, merge em `develop` e publicação exclusivamente em homologação para validação. O worker será instalado no rollout de homologação, mas o processamento RAW permanecerá desligado por fotógrafo por padrão. Esta autorização não inclui produção nem aprovação estética ou de compatibilidade de câmeras.

## Capabilities

### New Capabilities

- `media-storage/raw-development`: admissão e desenvolvimento temporário de RAWs, seleção/versionamento de motor e acompanhamento de atualização.

### Modified Capabilities

- `gallery-visualization-and-watermark-controls`: o carregamento administrativo poderá selecionar JPEG ou formatos RAW compatíveis para capa e pasta.
- `media-storage/staged-folder-release`: fotos RAW seguem o estado de preparação e somente ficam disponíveis após processamento e liberação válidos.
- `media-storage/protected-previews`: derivados poderão ser produzidos a partir do JPEG temporário desenvolvido, sem entregar nem reter permanentemente RAWs ou JPEGs de alta resolução.

## Impact

Worker isolado de desenvolvimento, adaptadores de motor, seleção e estado administrativo, verificação de versões do lançamento estável, validação de formato/câmera, limites de CPU/memória/disco, rotas de upload e integração com o pipeline facial e de prévias. A change também reconciliará o mandato e o roadmap com a nova decisão: RAW será aceito somente como fonte transitória para conversão, sem arquivo frio, cópia no Drive ou uso como entrega final.
