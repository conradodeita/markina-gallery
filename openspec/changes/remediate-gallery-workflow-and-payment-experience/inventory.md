## Inventário de produtores e consumidores

Inventário executado antes da alteração de modelo, conforme a task 1.1. A classificação abaixo cobre as ocorrências de `PhotoFolder`, capa, publicação, resumo, Vendas e Pagamentos encontradas em `backend/app`, `backend/tests` e `frontend/app`; buscas repetíveis usam `rg -n "PhotoFolder|cover_photo|payment-communications|folder_display_mode|release" backend frontend/app`.

### Backend — escrita

- `backend/app/main.py`: cria, renomeia e exclui pasta; registra/importa/exclui foto; escolhe/limpa capa; publica pasta; configura Vendas; decide e lista comunicações de pagamento.
- `backend/app/gallery_lifecycle.py` e `backend/app/gallery_cleanup.py`: removem ou retêm pastas/fotos durante o ciclo de vida e limpam a referência de capa.
- `backend/app/private_derivation.py`: cria referências privadas individuais a partir de fotos publicadas; não deve publicar pasta.
- `backend/app/worker.py` e `backend/app/media.py`: processam mídia e mensagens, mas não decidem publicação editorial.
- migrations `20260827_0005` a `20260831_0032`: produzem o schema atual; a nova migration parte exclusivamente de `20260831_0032`.

### Backend — leitura

- `backend/app/main.py`: editor, detalhes, fotos de capa, pastas, resumo, disponíveis por cliente, prévias administrativas/autorizadas, visualização pública/privada e painel de pagamentos.
- `backend/app/checkout.py`: valida fotos publicadas antes de gerar snapshot do pedido.
- `backend/app/private_derivation.py`: valida origem, pasta publicada e disponibilidade antes de criar referência privada.
- `backend/app/gallery_lifecycle.py`, `gallery_cleanup.py`, `commercial_removal.py` e `historical_media.py`: inventário, bloqueios comerciais, retenção histórica e limpeza segura.

### Frontend — consumidores

- `frontend/app/admin/galleries/sources/[sourceId]/edit/gallery-editor.tsx`: cinco etapas, Vendas, Detalhes, Imagens, publicação e Clientes.
- `frontend/app/admin/galleries/sources/[sourceId]/page.tsx`: resumo operacional da Galeria pública.
- `frontend/app/admin/galleries/sources/[sourceId]/preview/page.tsx`: prévia do fotógrafo.
- `frontend/app/admin/payments/page.tsx`: comunicações, decisões e retry.
- `frontend/app/gallery/[galleryId]/page.tsx` e componentes compartilhados de apresentação: galeria autorizada, seleção, favoritos e compra.
- rotas `frontend/app/api/**`: proxies transparentes; nenhuma delas deve reinterpretar propósito, disponibilidade ou estado financeiro.

### Classificação obrigatória

- Pastas `content`: aparecem em editor, resumo, ordenação, publicação e navegação autorizada.
- Pasta `cover_assets`: criada/reutilizada somente pelo upload de capa; fica fora de contagens, ordenação, publicação, checkout, derivação privada e navegação.
- Publicação: decisão exclusiva do endpoint administrativo de publicação; workers apenas processam derivados.
- Referência privada: criada exclusivamente por escolha administrativa na etapa Clientes ou por seleção transacional da própria cliente.
- Capa: referencia foto pronta da mesma Galeria pública, sem cópia; pode vir de `content` ou `cover_assets`.
- Pagamentos: estado financeiro vem de pedido/comunicação e snapshots, nunca do estado operacional da galeria.

Nenhuma ocorrência encontrada ficou sem uma das classificações acima.
