# Proposal

## Why

A prova open source aprovada usa Restic e Rclone no backup global e também no fluxo sintético de arquivo frio, mas a `main` ainda define `GoogleDriveMediaArchiveStorage` como o único adapter de mídia implementado. É necessário especificar como Rclone crypt poderia atender ao mesmo contrato de armazenamento sem criar uma segunda fila, catálogo, billing ou regra de retenção.

## What Changes

- Especificar um provider Rclone crypt para o contrato `MediaArchiveStorage`, mantendo compatibilidade com o executor e o adapter Google Drive existentes.
- Reutilizar o catálogo, chave opaca por objeto, propriedade e autorização tenant-scoped, readback integral e ciclo comercial de `add-gallery-media-archive`.
- Preservar as durações selecionáveis de recuperação fria de 7/14/30 dias e a janela normal de reabertura de 30 dias após expiração como regras separadas. Resultado incerto permanece com reserva em `reconciliation_required`; esta proposta não adiciona ação/API para resolver esse estado.
- Exigir transferência em blocos limitados, operações Rclone fixas, identidade/namespace de mídia próprios e falha fechada em config, metadados ou listagem inválidos.
- Manter sem decisão o modelo de identidade/roteamento do provider: IDs do catálogo e manifesto v1 não identificam provider, e binding tenant→provider sozinho não resolve objetos antigos se houver coexistência ou transição.
- Manter seleção de provider inativa por padrão e sem fallback automático; a composição de produção permanece bloqueada até decisão e gate operacional próprios.
- Planejar prova local sintética `crypt → local`; nenhuma credencial, remote externo, banco real, Drive, OAuth ou produção será usado.

## Capabilities

### New Capabilities

- `media-storage/rclone-media-archive-storage`: contrato observável do provider Rclone crypt para objetos frios tenant-scoped.

### Modified Capabilities

- `media-storage/gallery-media-archive`: preservar as regras existentes de ownership, isolamento, integridade, créditos, prazos e ausência de expurgo automático; acrescentar somente a compatibilidade com o provider injetado quando aprovado.

## Impact

- Ponto de extensão: `MediaArchiveStorage` e os fluxos existentes de execução de arquivo e recuperação.
- Código futuro provável: adapter Rclone, composição explicitamente configurada do worker e testes sintéticos de adapter/composição. Nenhum desses arquivos será alterado nesta etapa de proposta.
- Restic continua no repositório cifrado de backup global; mídia usa configuração, chave, raiz/prefixo e namespace separados, mesmo quando ambas as rotinas usam Rclone.
- O contrato atual recebe somente `remote_id` em leitura/exclusão e usa um storage por operação; qualquer coexistência/troca precisa definir identidade por objeto ou ciclo, roteamento de recuperação/exclusão e compatibilidade dos registros/manifestos existentes. Esta change mantém essa escolha como gate do proprietário e não propõe migration.
- Dependência de decisão/revisão: remote de destino suportado e sua custódia de configuração/chaves, capacidades exigidas do backend e forma autorizada de composição. Até isso ser definido, não implementar nem selecionar o provider no runtime.
