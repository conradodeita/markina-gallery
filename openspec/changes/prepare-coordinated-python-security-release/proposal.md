# Proposal

## Why

Oito consumidores ARM64 continuam com aiohttp 3.14.3, multidict 6.8.0, urllib3 2.7.0 e yarl 1.24.5. O web já publicado não deve mudar. O executor app existente só cobre API/web e os loops antigos não oferecem drenagem confirmada antes de SIGTERM. Uma contagem zero seguida de stop não impede um claim intermediário.

## What Changes

- Inventariar somente metadados dos oito consumidores e preparar correções isoladas dos quatro pacotes, preservando os demais pacotes e as camadas/base de cada imagem.
- Acrescentar ao executor app existente o escopo explícito python-security, com planejamento e simulação verificáveis, sem permitir que caia no fluxo API/web.
- Validar candidatos e imagens anteriores, ordem sequencial, receipts e rollback em simulação; recusar publicação real enquanto os contratos de drenagem e homologação não puderem ser demonstrados.
- Documentar evidências, limites de recursos e próximos pré-requisitos concretos. Implementação operacional incompleta SHALL permanecer bloqueada e identificada, sem anunciar GO.

## Capabilities

### New Capabilities
- Nenhuma.

### Modified Capabilities
- `deployment-operations`: preparação Python independente, segurança das filas e recusa explícita do executor para contratos ainda indisponíveis.

## Impact

Somente scripts, testes, CI proporcional e documentação/OpenSpec. A missão autoriza implementação e PR/merge com CI aprovado, mas proíbe qualquer deploy e qualquer mudança operacional na Oracle. Não modificar workers, bibliotecas, Dockerfiles oficiais, Compose ou modelos para contornar a ausência de drenagem. Os bloqueios observados não dispensam os builds e testes independentes viáveis.
