# Proposal

## Why

O worker de arquivo frio recebe um único adapter injetado, mas a reivindicação atual consulta a fila global de tenants ativos; o adapter Google Drive, por sua vez, fica preso a um único tenant. Ligar esses componentes sem uma fronteira de composição e seleção anterior ao claim pode entregar uma operação de outro tenant ao adapter do piloto. A task operacional 1.4 precisa de um contrato local e sintético para essa composição antes de qualquer ensaio real.

## What Changes

- Definir a composição explícita entre worker, tenant selecionado e `MediaArchiveStorage`, com validação do vínculo antes de descoberta, claim ou chamada externa.
- Delimitar o primeiro piloto ao tenant do proprietário: a seleção autorizada SHALL ocorrer antes de reivindicar operação; jobs e leases de outros tenants não são executados nem reatribuídos ao adapter do piloto.
- Preservar o coordenador/lease global existente, o contrato do executor e o adapter injetado; não selecionar provider Drive por ambiente nem ativar o worker por padrão.
- Separar o vínculo e a fonte de credencial de mídia das credenciais/factory do backup global. A identidade Workspace dedicada e a raiz própria já foram aprovadas; provisão/custódia e OAuth reais permanecem no gate operacional. O piloto local usa binding e transporte sintéticos.
- Definir regressões locais com fixtures, tokens e transporte sintéticos para gate inativo, configuração ausente/incompatível, isolamento de tenant e composição válida, sem rede Google.
- Manter a task operacional 1.4 aberta. Esta change é pré-requisito técnico para retomá-la e não seleciona raiz operacional, prova OAuth/quota, habilita tenants nem autoriza operação externa.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `media-storage`: adicionar o contrato de composição do storage de arquivo frio no worker e de claim restrito ao tenant explicitamente selecionado.

## Impact

- Fronteiras candidatas: `backend/app/worker.py`, `backend/app/media_archive_worker.py` e seus testes de dispatcher/claim/composição.
- A configuração/factory de credencial de mídia depende de decisão arquitetural; `WorkspaceDriveBackupStore` e `workspace_credentials` permanecem fora desse caminho.
- Delta OpenSpec em `media-storage`. A change existente `add-gallery-media-archive`, sua task 1.4, o runtime de backup e os artefatos da PR #414 não são alterados por esta proposta.
- Não há mudança de schema, migration, interface pública, segredo, configuração de produção, release ou chamada ao Drive nesta etapa.
