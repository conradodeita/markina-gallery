## Context

Veja `proposal.md` — Why. O inventário atual encontrou três limites estruturais dominantes: `.admin-shell` com 840 px, `.admin-content` com 1.180 px e `.client-content` com 960 px. A barra flutuante da seleção também para em 980 px, enquanto algumas páginas adicionam limites próprios de 1.180–1.440 px. Existem `max-width` legítimos para texto, formulário e diálogo, mas eles estão misturados aos limites de seção. A etapa 03 já envia capa para uma pasta técnica, porém o endpoint de Detalhes consulta todas as fotos da Galeria pública e o frontend renderiza todas como opções. A etapa 04 ainda expõe `Usar como capa`. No fluxo histórico, selecionar uma foto criava uma galeria privada; a decisão consolidada em `unify-gallery-client-collections` substituiu esse comportamento e mantém novas seleções na galeria canônica. A barra flutuante também apresenta um link primário cujo contraste pode ocultar o texto; a interface privada legada reutiliza a composição editorial completa, incluindo capa, e mantém comentários num bloco global com seletor de foto.

A mudança deve preservar autenticação, autorização, prévias protegidas, integridade galeria → pasta → foto, seleção e preço backend-driven. Não há necessidade de migration: a pasta `cover_assets` e `cover_photo_id` já existem.

## Goals / Non-Goals

**Goals:**

- estabelecer uma única fundação fluida para todas as rotas antes de ajustar componentes locais;
- classificar e preservar somente limites de largura que protegem legibilidade ou viewport;
- retirar consultas e controles duplicados de capa sem apagar capas existentes;
- tornar o avanço, a revisão e os comentários da cliente contextuais e acessíveis;
- validar desktop largo, notebook, tablet e smartphone sem overflow horizontal.

**Non-Goals:**

- alterar autorização, preços, pedidos, pagamentos, retenção ou proteção dos arquivos;
- criar um editor livre de layout, novos templates ou configuração arbitrária de CSS;
- trocar o pipeline JPEG, copiar fotos de capa para pastas de conteúdo ou expor originais;
- transformar todos os textos e formulários em linhas excessivamente largas.

## Decisions

### Tokens de gutter e shells fluidos como causa estrutural

Os shells globais passarão a usar `width: 100%`, `max-width: none`, `box-sizing: border-box` e padding lateral baseado em um token fluido com `clamp()`. `admin-content`, `client-content` e `admin-shell` compartilharão essa regra; topbars alinharão seu padding ao mesmo token, sem cálculo baseado num container central. O canvas de autenticação também ocupará a viewport, mas o card do formulário conservará sua medida curta.

Todos os `max-width` do frontend serão classificados em três grupos: estrutural, legibilidade e viewport. Limites estruturais em páginas, grids e barras serão removidos ou substituídos por largura fluida. Limites de texto em `ch`, formulários curtos e diálogos limitados pela viewport permanecerão. Exceções de largura por rota serão eliminadas quando a regra global as tornar redundantes.

Alternativa descartada: adicionar uma classe larga somente às telas reportadas. Isso perpetuaria os três shells estreitos, criaria divergência entre rotas e contrariaria a regra global solicitada.

### Grids responsivos orientados ao espaço disponível

Grids de cards e listas visuais usarão `repeat(auto-fit|auto-fill, minmax(...))` quando os itens forem homogêneos. Grids editoriais de fotografia manterão ordem DOM e regras de span existentes, mas ganharão colunas adicionais somente quando houver largura mínima útil por foto; os breakpoints de tablet e mobile continuarão explícitos. Componentes internos adotarão `min-width: 0`, quebra de texto e empilhamento para impedir overflow.

Alternativa descartada: apenas aumentar o número fixo de colunas. Isso diminuiria os cards em telas intermediárias e não corrigiria páginas não fotográficas.

### Capa enviada torna-se intenção vigente sem corrida entre uploads

O registro do upload continuará criando/reutilizando a foto na pasta técnica `cover_assets`. Quando o envio do JPEG for aceito pela rota de origem, o backend definirá `cover_photo_id` para esse ativo antes de enfileirar o derivado. Assim, a intenção mais recente fica persistida imediatamente; a prévia permanece ausente/processando até o derivado ficar pronto. Um upload anterior que terminar depois não recupera a preferência, porque o worker apenas gera derivados e não altera `cover_photo_id`.

O endpoint de Detalhes deixará de varrer fotos `content`. Ele retornará a configuração e, no máximo, o estado da capa vigente, mantendo temporariamente `cover_options` compatível com zero ou um item para consumidores anteriores. Capas legadas de conteúdo continuam servidas, mas não abrem novamente a escolha entre o acervo. O frontend elimina a galeria de opções; upload, estado, substituição e controles tipográficos formam o único fluxo.

Alternativa descartada: definir a capa somente quando o worker terminar. Dois uploads concorrentes poderiam concluir fora de ordem e escolher uma imagem antiga; também exigiria um estado de intenção novo.

### Etapa 04 permanece exclusivamente operacional para conteúdo

O botão e a função de definir capa serão removidos dos cards de foto. O backend pode manter `is_cover` durante compatibilidade sem que a interface o use, evitando ampliar desnecessariamente o contrato. Ampliação, seleção em massa, exclusão e estados continuam intactos.

Alternativa descartada: apenas esconder o botão com CSS. O controle continuaria no DOM, acessível por teclado/leitor de tela e coberto por lógica não desejada.

### Revisão da seleção separada da apresentação editorial

A Galeria pública conservará sua capa editorial e o CTA flutuante exibirá `Prosseguir`, direcionando para `/library/cart`, a tela de revisão e checkout. Essa tela consome a projeção do carrinho do backend, que contém apenas as fotos selecionadas e o resumo comercial; a capa não integra a lista nem o total. As prévias continuam protegidas, e a aparência editorial da galeria não muda.

O visualizador compartilhado receberá uma extensão opcional para conteúdo contextual da foto ampliada e uma notificação de mudança do item ativo. A página privada usará essa extensão para carregar e renderizar comentários da foto sob a mídia, com formulário e exclusão autorizados. O bloco global com seletor será removido. A Galeria pública e a prévia administrativa não passam essa extensão e permanecem inalteradas.

Alternativa descartada: duplicar um segundo visualizador exclusivo da seleção. Isso dividiria foco, teclado, swipe, proteção e manutenção de layout.

### Comentário e favorito contextualizados na prévia da compra

O painel Vendas e pagamentos e o HTML já gerado para fotos compradas usarão as tabelas `PhotoComment` e `PhotoFavorite` existentes, sem nova migration. O vínculo precisa respeitar simultaneamente tenant, cliente, foto e o escopo congelado no pedido: `derived_gallery_id_snapshot` quando presente; caso contrário, `parent_gallery_id_snapshot`. Assim uma interação de outra cliente ou de outra galeria que reutilize a mesma foto não aparece no pedido atual.

O backend fará consultas em lote para as fotos dos pedidos da página, sem uma consulta por item. Para cada combinação de cliente, escopo e foto, escolherá o comentário ativo mais recente e retornará um trecho de no máximo 50 caracteres; quando houver corte, o último caractere será uma elipse para manter o limite. O conteúdo integral e os registros existentes não serão modificados. O favorito será um booleano daquele mesmo vínculo.

No cartão de Vendas e pagamentos, o comentário ficará em texto legível logo abaixo do nome e do valor unitário, sem cobrir a miniatura ou a imagem ampliada; o coração permanece sobre a prévia disponível. Esse posicionamento deixa todas as interações da foto juntas no item do pedido e funciona para pastas públicas e privadas. Para o HTML independente de fotos compradas, permanece a sobreposição compacta e responsiva de comentário e coração já aprovada. O link de download enviará apenas a cor `--mk-brand` atualmente computada; o backend aceitará somente formato hexadecimal estrito e usará um padrão seguro caso ausente ou inválido. Comentário será escapado por `html.escape`; os cabeçalhos privados e a proteção de mídia existentes serão preservados. Sem imagem de prévia, nenhum overlay do HTML será renderizado.

Alternativa descartada: mostrar todas as interações ou consultar uma rota adicional para cada miniatura. Uma única anotação recente oferece contexto no espaço limitado e consultas em lote preservam o desempenho, sem alterar a página de comentários já existente.

### Card de pasta privada no acervo da cliente

No `Acervo da cliente`, o conteúdo expandido de cada pasta será separado do cabeçalho recolhível por um divisor e espaçamento consistente. Estado da mídia, ações, configuração de prazo, clientes autorizadas, grade de fotos e upload terão blocos com largura mínima controlada. `Processamento da pasta` usará o botão secundário comum; `Disponibilizar fotos prontas` terá o estilo primário; renomear e excluir ficarão no mesmo grupo, com excluir usando o tratamento visual de ação destrutiva. Em telas estreitas, as ações quebrarão em duas colunas ou empilharão sem forçar o texto nem a grade para fora da tela.

O controle de dias de acesso ficará compacto com a unidade `dias` visível ao lado. A regra temporal e de arquivo frio é detalhada na change `add-gallery-media-archive`; aqui se trata do espaço e da hierarquia responsiva do componente compartilhado.

### Hierarquia da página Configurações

Configurações terá navegação interna e grupos recolhíveis com details/summary nativos. A ordem será: primeiros passos e progresso; acesso e segurança; WhatsApp e comunicação; recebimentos (PIX e provedores); marca e aparência (textos da entrada, ativos e proteção visual); encerramento da conta; Termos de uso. Primeiros passos inicia aberto; os demais fechados. Cada grupo tem título/contexto visíveis, teclado/foco e indicador de expansão. Recolher não desmonta formulários nem apaga preenchimentos. Links internos e fragmentos iniciais/hashchange abrem os details ancestrais do destino e o posicionam na tela, inclusive links já existentes para PIX, WhatsApp e onboarding.

O resumo de onboarding continua no início e mantém o estado de cada etapa. A linha de Termos passa a explicar que o aceite completo está no fim e oferece um link âncora. O formulário, a cópia/histórico de aceite e o aceite atual serão renderizados somente na última seção, depois do encerramento da conta. Assim o estado de prontidão continua visível sem repetir os Termos entre os controles de configuração.

Em telas estreitas, os links internos podem quebrar em linhas ou rolar horizontalmente com affordance visível; títulos, descrições e áreas de foco permanecem legíveis. A ordem DOM seguirá a mesma ordem visual, inclusive o aceite no fim.

## Risks / Trade-offs

Copy do encerramento aprovada em 11/11/2026: no card de Configurações, a consequência de acesso será somente “Depois de encerrada, você não poderá entrar na conta.” Remover dessa frase a possibilidade de restauração pelo proprietário é ajuste de apresentação; não modifica o fluxo operacional de recuperação/reabertura especificado na change de encerramento.

Orientação textual do canal transacional, aprovada em 11/11/2026: explicar que OTP e avisos usam o número próprio pareado, recomendar número de negócios em vez do pessoal, manter a informação de segurança sobre API key/sessão/QR e orientar adicionar o número e escanear o QR Code como no WhatsApp Web. Ajuste somente de copy, sem alterar o pareamento ou a persistência.

- [Conteúdo excessivamente largo em monitores ultrawide] → limitar somente medidas de leitura internas e definir tamanho mínimo útil dos cards, mantendo seções fluidas.
- [Grids automáticos mudarem ordem ou densidade] → preservar ordem DOM, testar pontos de quebra e não usar CSS columns/masonry que altere leitura.
- [Upload interrompido deixar capa pendente] → mostrar estado explícito e permitir substituição; a capa anterior poderá continuar como fallback visual até o novo derivado ficar pronto se o contrato assim indicar.
- [Consumidor antigo depender de várias `cover_options`] → manter a chave temporariamente com apenas a capa vigente e migrar todos os consumidores oficiais no mesmo deploy.
- [Comentários ampliarem a altura do lightbox] → dividir mídia e painel contextual, limitar o conjunto ao viewport e permitir rolagem interna acessível sem reduzir a imagem abaixo de um mínimo útil.
- [Comentário ser difícil de ler ou competir com a miniatura] → limitar o trecho a 50 caracteres e apresentá-lo abaixo do nome e do valor no cartão administrativo, com quebra de linha responsiva; manter o overlay no HTML independente e verificar os dois formatos.
- [Interação de cliente incorreta aparecer no pedido] → filtrar por tenant, cliente, foto e escopo congelado no pedido; cobrir pedidos de galeria derivada e canônica com testes.
- [Tema ou comentário manipular estilo/documento exportado] → aceitar só uma cor hexadecimal validada, escapar texto HTML e testar conteúdo semelhante a marcação.
- [Regra global quebrar páginas densas] → criar inventário automatizado dos limites, testes estruturais dos shells e revisão visual em quatro viewports antes do deploy.

## Migration Plan

1. Adicionar testes dos shells e inventário dos limites; trocar tokens/wrappers compartilhados antes de qualquer exceção local.
2. Revisar grids, tabelas, cards, barras, imagens e media queries por categoria, removendo limites estruturais redundantes.
3. Alterar o contrato de Detalhes e a intenção de capa, migrar a etapa 03 e retirar a ação da etapa 04 com testes de concorrência/compatibilidade.
4. Corrigir CTA, revisão sem capa e comentários no visualizador compartilhado.
5. Vincular comentários e favoritos ao cliente, à foto e ao escopo do pedido no cartão de Vendas e pagamentos e no HTML de fotos compradas.
6. Executar testes frontend/backend, lint, typecheck, build, OpenSpec estrito e revisão visual em desktop largo, notebook, tablet e smartphone.
7. Após inventário e autorização humana específica, publicar pelo Compose `markina-gallery`, validar healthchecks e repetir o roteiro autenticado.

Rollback de código restaura os consumidores anteriores; a resposta compatível de `cover_options` e o modelo existente evitam migration. Nenhuma foto, capa, seleção, comentário ou pedido será apagado durante deploy ou rollback.
