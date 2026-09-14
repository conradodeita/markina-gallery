## Why

O proprietário quer uma alternativa escura à interface clara e uma capa mais limpa, sem marca-d'água nem linhas sobre a fotografia que já recebe o título. Também quer padronizar novos uploads de capa em orientação horizontal.

## What Changes

- Oferecer seleção de aparência claro/escuro/sistema no topo, para admin e cliente, com preferência local persistente e contraste consistente em páginas, cards, formulários e diálogos.
- Preservar a paleta preto/amarelo/cinza/bege; não aplicar inversão, filtro ou alteração de cor às fotos, logos ou QR Code.
- Retirar marca-d'água e grade somente na apresentação da capa, mantendo título, autenticação, autorização, resolução reduzida e remoção de EXIF/GPS.
- Manter proteção nas fotos de conteúdo, inclusive se uma mesma foto tiver sido usada como capa no fluxo legado.
- **BREAKING**: novos uploads/substituições de capa aceitam somente JPEG horizontal (largura maior que altura depois de corrigir orientação EXIF). Fotos quadradas/verticais recebem mensagem clara sem substituir a capa atual. Uploads comuns continuam aceitando qualquer orientação.
- Preservar capas já cadastradas; a nova restrição aplica-se aos próximos uploads. A apresentação limpa utiliza o derivado administrativo existente, sem alterar arquivos originais ou reprocessar o acervo.

## Capabilities

### New Capabilities

- `appearance-preference`: escolha persistente e acessível de tema para todo o website e PWA.

### Modified Capabilities

- `media-storage/protected-previews`: exceção restrita à capa autenticada, sem proteção visual e sem acesso ao original.
- `gallery-visualization-and-watermark-controls`: validação de capa horizontal, apresentação responsiva e proteção preservada nas fotos de conteúdo.

## Impact

Frontend compartilhado, tokens/CSS, controles de aparência e etapa 03; backend de upload e endpoints específicos de capa; testes e documentos de proteção visual. Sem novo motor de imagem, dependência externa, alteração financeira/facial, cache offline privado, migration destrutiva ou operação no servidor.

A evolução anterior `gallery-preview-exposure-and-installable-ui` está mergeada em develop (PR #82, `eb8c0837e3144f8d27429dffc05bb3683169d59a`), mas sua publicação ainda aguarda confirmação do inventário; este pedido prioriza a nova change e não confirma aquele deploy. A mudança atual depende dos tokens dessa evolução. Não sincronizar/arquivar a anterior nem declarar paridade antes da revisão/publicação próprias.
