## Why

A etapa Imagens mistura configurações padrão da galeria, controles da pasta selecionada e estados globais. Isso repete informações, dificulta entender a qual pasta cada valor pertence e ocupa espaço excessivo no celular. Durante uploads longos, o contador também desaparece e atualizações da tela causam piscadas.

## What Changes

- Apresentar uma visão única de reconhecimento facial e ajuste automático vinculada à pasta selecionada, para pastas públicas e privadas. Ao selecionar outra pasta, seus parâmetros, estados e progresso substituem os anteriores na mesma área.
- Manter configuração e progresso isolados por pasta. A lista de pastas mostra resumos compactos de contagem e upload para cada pasta; o painel único mostra controles e detalhes da pasta selecionada.
- Salvar automaticamente mudanças de intensidade e exposição e iniciar o reprocessamento somente da pasta selecionada, sem ações manuais de salvar ou processar a galeria.
- Manter visível o progresso real de cada lote de upload, identificado por pasta, mesmo quando a seleção muda. Atualizações de progresso não devem remontar ou piscar a tela.
- Preservar o isolamento por fotógrafo e validar as filas/telemetria exibidas pelo Monitor do sistema durante reprocessamento e seleção de pastas.
- Remover controles, estados e handlers que se tornarem comprovadamente obsoletos somente nesta página e neste fluxo, com os testes correspondentes.

## Capabilities

### New Capabilities

- `media-storage/unified-folder-processing`: controles e processamento independentes por pasta em galerias públicas e privadas.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: progresso de upload por pasta permanece visível e estável na etapa Imagens.

## Impact

Etapa Imagens do editor administrativo; contrato existente de leitura e gravação da configuração por pasta; consultas de progresso facial e de ajuste; atualização do estado de uploads no cliente; testes direcionados de interface e contrato. A mudança preserva os defaults atuais por tipo de pasta, os gates faciais globais, os fluxos de proteção/publicação e o pipeline de JPEG/RAW.

## Non-goals

- Refatorar componentes ou telas fora da etapa Imagens e do fluxo de processamento por pasta.
- Mudar os valores padrão atuais de pastas públicas ou privadas, nem copiar parâmetros entre galeria, pastas ou tipos de pasta.
- Alterar o processamento de capas, o motor RAW/JPEG, o reconhecimento facial global, permissões, consentimento, proteção de prévias, retenção ou publicação.
- Permitir pausar ou contornar o gate facial global por pasta.
