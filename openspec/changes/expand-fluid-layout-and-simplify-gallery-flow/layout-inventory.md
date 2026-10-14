## Inventário de largura estrutural

Levantamento executado antes das alterações com buscas em `frontend/app/**/*.css`, `frontend/app/**/*.tsx` e `frontend/app/**/*.ts` por `max-width`, `width: min(...)`, `container`, larguras fixas e centralização por `calc((100vw - ...)/2)`. Ocorrências em `.next`, `node_modules`, caches e arquivos gerados foram excluídas.

### Limites estruturais — remover ou tornar fluidos

| Origem | Seletor | Limite atual | Destino |
| --- | --- | --- | --- |
| `globals.css` | `.admin-shell` | 840 px, centralizado | largura total com gutter global |
| `globals.css` | `.admin-content` | 1.180 px, centralizado | largura total com gutter global |
| `globals.css` | `.admin-topbar` | centralização calculada em 1.180 px | padding pelo mesmo gutter global |
| `globals.css` | `.client-content` | 960 px, centralizado | largura total com gutter global |
| `globals.css` | `.client-topbar` | centralização calculada em 960 px | padding pelo mesmo gutter global |
| `globals.css` | `.public-gallery-shell` | 1.760 px | largura total com gutter global |
| `globals.css` | `.selection-summary--floating` | 980 px, centralizado | largura total disponível com gutter e safe area |
| `globals.css` | `.gallery-editor-shell` | 1.080 px | remover limite da seção |
| `globals.css` | `.gallery-preview-page` | 1.120 px | remover limite da seção |
| `globals.css` | `.admin-shell:has(.photo-card-grid)` | 1.240 px | eliminar exceção; shell já será fluido |
| `globals.css` | `.pricing-presets-page` | 1.180 px | remover limite da página |
| `globals.css` | `.client-directory-shell` | 1.180 px | remover limite da página |
| `globals.css` | `.client-checkout-review` | 980 px, centralizado | remover limite da revisão |
| `globals.css` | `.private-gallery-detail` | 1.180 px | remover limite da página |
| `globals.css` | `.admin-notifications-page` | 1.120 px | remover limite da página |

### Limites de legibilidade — preservar no conteúdo interno

| Origem | Seletor | Motivo |
| --- | --- | --- |
| `design-system.css` | `.mk-page-heading p:not(.eyebrow)` (66ch) | texto corrido |
| `design-system.css` | `.dashboard-context p` (60ch) | texto corrido |
| `design-system.css` | `.dashboard-section-detail` (45ch) | texto corrido |
| `design-system.css` | `.selection-summary p` (54ch) | texto corrido |
| `globals.css` | `.dashboard-hero h1` / parágrafo (650/590 px) | medida editorial interna; não limita o hero |
| `globals.css` | `.gallery-list-heading > div`, `.gallery-editor-heading > div` (760 px) | bloco textual do cabeçalho |
| `globals.css` | `.gallery-create-shell`, `.gallery-settings-form` (760 px) | formulário sequencial; a seção externa continuará fluida |
| `globals.css` | `.gallery-presentation-title` e `.gallery-presentation-context` | legibilidade sobre mídia |
| `globals.css` | `.security-result` (620 px) | credencial/formulário de leitura sequencial |
| `globals.css` | `.facial-search-panel` texto (64ch) | texto explicativo |

### Limites de viewport ou controles intrínsecos — preservar

| Origem | Seletor | Motivo |
| --- | --- | --- |
| `globals.css` | `.auth-card` (440 px) | formulário curto dentro de canvas full-width |
| `globals.css` | `.auth-brand-logo` (180 px) | dimensão intrínseca de marca |
| `globals.css` | `.mk-dialog`, `.lifecycle-dialog`, `.administrative-private-dialog`, `.gallery-presentation-dialog`, `.facial-consent-dialog` | diálogo limitado pela viewport e conteúdo |
| `globals.css` | `.photo-preview-dialog > div` | visualizador limitado pela viewport, não por shell |
| `globals.css` | `.client-directory-toolbar label` (360 px) | campo de busca interno |
| `globals.css` | `.whatsapp-pairing-qr`, `.client-checkout-qr`, `.gallery-pix-qr` | QR com dimensão operacional |
| `globals.css` | `.whatsapp-pairing-code` (360 px) | código curto e quebrável |
| `globals.css` | `.gallery-customization-preview-image strong`, `.watermark-preview`, `.preview-dynamic-mark` | texto posicionado dentro de mídia |
| `globals.css` | `.selection-summary--floating details ul` | popover limitado à viewport |
| `globals.css` | media queries `@media (max-width: ...)` | breakpoints responsivos, não containers estruturais |
| CSS compartilhado | ícones, badges, marcadores e colunas mínimas | dimensões intrínsecas; revisar apenas se produzirem overflow |

### Grids e mídias a revisar

- Grids homogêneos (`gallery-card-grid`, pastas, bibliotecas, cards de fotos, diretório e resultados faciais) devem usar `auto-fit`/`auto-fill` com mínimo útil.
- Grids editoriais de fotos devem conservar a ordem DOM e adaptar a quantidade de colunas por breakpoint, sem masonry por CSS columns.
- Cards, células e filhos de flex/grid devem receber `min-width: 0` onde conteúdo longo possa forçar overflow.
- Imagens e vídeos compartilhados devem usar a largura do container com `height: auto` ou `object-fit` explícito quando houver caixa com proporção definida.
- Tabelas densas podem manter rolagem horizontal local; não devem ampliar a página inteira.

Não foram encontradas classes utilitárias `container`, `max-w-*` ou `mx-auto` no código de produção TSX. A ocorrência `container` em teste é apenas a variável retornada pelo Testing Library.
