# Proposal

## Why

Depois que uma pasta é liberada, a interface deixa de oferecer renomeação e a API recusa a alteração, mesmo quando o fotógrafo só precisa corrigir o título. Pastas restritas criadas no `Acervo da cliente` e pastas exclusivas ainda administradas em uma Galeria privada legada também não têm ação própria para renomear.

## What Changes

- Permitir que o fotógrafo renomeie pastas comuns e restritas da Galeria pública antes ou depois da liberação, enquanto a galeria permanecer editável.
- Permitir renomear pastas existentes na tela de uma Galeria privada legada, sem reabrir seu fluxo de criação nem ampliar sua administração.
- Expor a ação no editor de Imagens, no card `Acervo da cliente` e na gestão já existente de pastas da Galeria privada legada.
- Preservar público, atribuições, fotos, seleções, pedidos, ledger e snapshots históricos ao trocar somente o nome da pasta.
- Validar o nome após remover espaços externos e rejeitar nomes vazios ou maiores que 200 caracteres.

## Capabilities

### New Capabilities

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: permitir editar o nome de pastas comuns e restritas já liberadas pela interface administrativa.
- `client-access/folder-audiences`: apresentar o nome atualizado somente às clientes autorizadas à pasta, sem modificar a audiência.

## Impact

- API autenticada `PATCH /admin/photo-folders/{folder_id}` e auditoria existente `photo_folder.renamed`.
- Next.js: editor de Imagens da Galeria pública, seção `Acervo da cliente` nos cards e tela existente de gestão da Galeria privada legada.
- Testes de API e interface; nenhuma migration, mudança de armazenamento ou escrita em produção.
