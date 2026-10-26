# Proposal

## Why

LightCraft não atingiu a qualidade esperada e Gemma não trouxe benefício suficiente frente ao YuNet + SFace, que continua sendo o motor facial aprovado. A remoção reduz dependências, imagens e superfícies operacionais especializadas sem mudar a busca SFace nem o ajuste opcional de prévias.

## What Changes

- **BREAKING** Remover a admissão e o processamento de arquivos RAW, inclusive o caminho LightCraft; galerias continuam recebendo JPEGs pelo fluxo vigente.
- Remover seleção, APIs, workers, dependências, imagem e configuração operacional do Gemma; YuNet + SFace será o único motor servido e configurável para clientes.
- Manter o worker independente de ajuste de prévias baseado em RawTherapee e fixá-lo em 5.13, com artefato e checksum por arquitetura.
- Preservar dados existentes, migrations históricas e registros de buscas; nenhuma tabela, embedding, volume ou imagem operacional será apagada por esta change.
- Documentar gates de inventário/filas antes de qualquer desativação remota; esta change não autoriza migration, limpeza Docker, reinício ou deploy.

## Capabilities

### New Capabilities

- `privacy-biometric/facial-search-engine`: busca facial servida exclusivamente por YuNet + SFace, sem seletor de motor experimental.

### Modified Capabilities

- `gallery-visualization-and-watermark-controls`: envio de imagens pelo painel fica restrito a JPEG.
- `media-storage/protected-previews`: derivados e análise facial continuam no fluxo JPEG; não há ingestão de RAW.

## Impact

Backend FastAPI/SQLAlchemy e migrations futuras, workers de mídia/faciais, Dockerfiles e Compose, Nginx, frontend administrativo e seleção de arquivos, CI, documentação do roadmap e inventário de terceiros. O schema implantado informado pelo proprietário é 0089; o `origin/main` atualizado também tem head Alembic 0089. A remoção manterá essa compatibilidade sem migration destrutiva. RawTherapee será atualizado apenas no worker opcional de ajuste de prévias.

## Operational authorization

Em 26/10/2026, o proprietário autorizou explicitamente a correção até merge e deploy bem-sucedido. Essa autorização amplia o escopo operacional anterior, condicionada a CI verde, inventário atual, preservação do schema/dados, plano de impacto zero, validação e recuperação compatível. Não autoriza excluir imagens, volumes, histórico biométrico ou dados de clientes. O procedimento será registrado em `deployment.md` antes de qualquer mutação remota.
