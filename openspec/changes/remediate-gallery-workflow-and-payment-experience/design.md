## Context

Consulte `proposal.md` — Why. A API da Galeria pública já expõe `/sales` como disponível e persiste faixas, PIX, mensagem, prazo e interações, mas o componente do editor tipa essa resposta como indisponível e sempre renderiza um placeholder. A capa, por sua vez, só pode apontar para `PhotoAsset` já processado dentro de uma pasta, o que obriga o primeiro upload a acontecer na etapa Imagens.

Pastas usam hoje `preparing` ou `released`; o endpoint de liberação mistura duas decisões: marca a pasta como concluída e cria referências `admin` em galerias privadas escolhidas. A listagem de fotos administrativas para a etapa Clientes considera somente pastas `released`, por isso “Disponibilizar fotos” fica desabilitado enquanto o fluxo anterior não for concluído. O resumo já recebe miniatura por pasta e métricas avançadas por cliente em contratos correlatos, mas sua interface reduz esses dados a linhas sem ação. Pagamentos lista comunicações em sequência e consulta entidades relacionadas por item, sem filtros nem agrupamento.

A composição compartilhada já preserva autorização, marca-d’água e visualizador, porém força cartões de proporção uniforme e não recebe dimensões suficientes para organizar retratos e paisagens. A mudança atravessa modelo, APIs e múltiplas superfícies Next.js, mas deve preservar o ciclo de vida comercial implantado, as galerias privadas sem cópia de mídia e a autenticação anterior a qualquer prévia.

## Goals / Non-Goals

**Goals:**

- corrigir os fluxos que já possuem backend e remover o acoplamento entre publicação editorial e cliente privado;
- permitir configurar a primeira capa sem quebrar a propriedade obrigatória galeria → pasta → foto;
- manter fotos já publicadas disponíveis durante uma rodada adicional na mesma pasta;
- tornar resumo, Clientes e Pagamentos superfícies de operação backend-driven e reutilizáveis;
- preservar proporção, ordem acessível e desempenho na visualização compartilhada;
- manter compatibilidade de leitura com dados e referências privadas existentes.

**Non-Goals:**

- automatizar confirmação PIX, conciliação bancária, anexar comprovante ou integrar Infinity Pay;
- apagar ou reclassificar pedidos, compras, galerias privadas ou referências existentes durante a migration;
- transformar tipografia e layout em editor livre de página ou aceitar CSS fornecido pelo fotógrafo;
- expor grade coletiva, original, download ou prévia antes do OTP;
- ativar busca facial, alterar Evolution API ou configurar credenciais externas;
- fazer deploy nesta fase de planejamento.

## Decisions

### Capa dedicada continua obedecendo à hierarquia de mídia

`PhotoFolder` receberá um propósito controlado `content | cover_assets`, com backfill `content` e unicidade parcial de uma pasta técnica de capa por Galeria pública. O upload da etapa 03 usa o mesmo pipeline de validação JPEG, armazenamento, remoção de metadados e geração de derivados; a API cria ou reutiliza a pasta técnica e registra a foto nela. Pastas `cover_assets` não entram em contagens, ordenação, publicação, filtros de fotos disponíveis nem navegação da cliente.

A capa continuará sendo uma referência `cover_photo_id` a uma foto da própria origem. O fotógrafo também poderá escolher foto pronta de pasta `content`; nenhuma cópia será criada. Excluir uma capa dedicada seguirá a política administrativa de mídia e limpará a referência. Fotos de capa dedicadas permanecem protegidas e só são servidas pelo contrato de capa autorizado.

Alternativa descartada: permitir `PhotoAsset.folder_id` nulo ou criar armazenamento paralelo fora do pipeline. Ambas quebrariam a integridade recém-estabelecida e duplicariam validação/limpeza.

### Vendas reutiliza o contrato da Galeria pública

O editor passará a consumir o payload real de `/admin/parent-galleries/{id}/sales`. Um componente comercial controlado reunirá faixas, simulador, PIX, mensagem, prazo, favoritos e comentários, reaproveitando regras de transformação testáveis em vez de redirecionar para a tela legada de galeria privada. O `PUT` será a única persistência e pedidos continuarão lendo snapshots no checkout.

O contrato de galeria privada permanecerá compatível para leitura herdada durante a transição, mas novas edições visíveis serão direcionadas à Galeria pública.

Alternativa descartada: manter Vendas como atalho para `/admin/galleries/{derived}/pricing`. Isso exige uma privada já criada, duplica configuração herdada e não atende uma Galeria pública sem clientes.

### Publicação deixa de criar referências privadas

Será criado um contrato de publicação de pasta/rodada que não recebe `gallery_ids`. Na primeira publicação, a pasta torna-se `released` e somente fotos com derivado pronto passam a `available=true`. Em pasta já publicada, uploads adicionais serão aceitos com `available=false`; conteúdo anterior mantém `available=true`. Uma nova publicação promove apenas os itens prontos ainda indisponíveis, registra contagens e deixa falhas fora do lote.

O endpoint legado `/release` aceitará temporariamente apenas payload sem destinos e encaminhará à nova semântica; `gallery_ids` não vazio receberá resposta de contrato descontinuado sem criar referências. A criação de `DerivedGalleryPhoto(origin=admin)` ocorrerá somente na etapa Clientes, para as fotos escolhidas. Seleção da cliente continuará criando origem `client` pelo serviço transacional vigente.

Alternativa descartada: publicar automaticamente ao concluir o processamento. Isso pode expor arquivos ainda não revisados e elimina a fronteira segura entre upload e disponibilidade.

### Resumo abre a pasta por destino interno validado

Cards de pasta usarão a miniatura protegida já retornada pelo backend e navegarão para a etapa Imagens com `folder=<uuid>` como parâmetro interno. O editor confrontará esse identificador com as pastas carregadas da Galeria pública antes de abrir a área de trabalho; um valor inválido não produzirá consulta fora do escopo. A mesma área suportará pasta em preparação ou publicada, diferenciando fotos disponíveis, prontas para publicar, processando e falhas.

Os cards de cliente serão extraídos como componente comum entre etapa 05 e resumo. A API agregará em lote contadores, `gallery_status` e `commercial_status` com precedência documentada: `pending_review`, `awaiting_payment`, `paid`, `overdue`, `cancelled` e `no_order`. Estado da galeria e estado comercial permanecerão badges separados para não confundir acesso com pagamento.

Alternativa descartada: construir resumo por chamadas individuais a cada privada/pedido. Isso cria N+1, estados transitórios incoerentes e lógica de precedência no navegador.

### Pagamentos usa consulta agregada e compatível

`GET /admin/payment-communications` ganhará filtros validados (`query`, `parent_gallery_id`, `financial_status`, `delivery_status`, `created_from`, `created_to`, cursor/limite) e devolverá `summary`, `facets`, `groups` por cliente e a lista plana compatível durante uma janela de transição. A consulta fará joins/snapshots em lote e não dependerá da existência da galeria operacional.

Cada grupo conterá pedidos/comunicações com estados e ações explicitamente devolvidos pelo backend. O frontend usará `details`/painel recolhível para filtros, cards com badges textuais e regiões expansíveis para informações e mensagens. Decisão e retry continuarão nos endpoints atuais, e o card será atualizado pela resposta ou por nova consulta sem mutação otimista do estado financeiro.

Alternativa descartada: agrupar a lista atual somente no frontend. Isso não resolve filtros, paginação, N+1 nem contagens coerentes do conjunto consultado.

### Tipografias são tokens locais, não nomes CSS livres

Será criado um registro compartilhado de tokens de fonte com nome de produto, categoria, stack de fallback e família CSS. As famílias adicionais serão arquivos WOFF2 locais sob licença compatível e acompanhados do texto de licença. A API persistirá somente tokens permitidos; valores legados conhecidos serão mapeados, e desconhecidos usarão fallback seguro na leitura até correção explícita.

A lista inicial terá ao menos duas famílias sem serifa, duas serifadas/editoriais e duas manuscritas, além dos fallbacks do sistema. A prévia e a apresentação usarão o mesmo token, impedindo divergência entre etapa 03 e galeria entregue.

Alternativa descartada: `@import` ou Google Fonts em runtime. Além de depender de terceiro, isso introduz rastreamento, falha offline e comportamento de cache fora do controle do produto.

### Grade editorial preserva DOM e proporção

Os contratos de foto incluirão largura e altura já disponíveis no ativo ou derivado. O componente calculará classes/variáveis de span a partir da razão limitada e manterá a ordem do DOM, usando CSS Grid responsivo com fallback de proporção conhecida e `object-fit: contain`. Fotos não terão moldura, sombra ou fundo de card dominante; controles ficarão sobrepostos ou numa faixa discreta. O visualizador continuará usando a mesma URL protegida.

No papel da cliente, coração, seleção e compra serão estados independentes e acessíveis, com botão de favorito separado do botão de ampliação. Na prévia administrativa, esses controles não serão renderizados. O layout `sequential` mostrará todas as pastas em sequência; `individual` manterá navegação por coleção.

Alternativa descartada: CSS columns puro. Apesar do efeito de masonry simples, ele altera a ordem visual por coluna em relação ao DOM e prejudica navegação por teclado/leitor de tela.

## Risks / Trade-offs

- [Pasta técnica aparece em consultas antigas] → filtrar por propósito em contratos, contagens, exclusão e publicação; adicionar regressões de autorização e inventário.
- [Mudança de `/release` afeta consumidor antigo] → manter adaptador para payload vazio, retornar erro explícito para destinos e migrar todos os consumidores/testes no mesmo conjunto.
- [Upload em pasta publicada expõe foto cedo] → criar item como indisponível e exigir publicação explícita após derivado pronto.
- [Fonte aumenta bundle] → versionar somente pesos realmente usados, WOFF2 subsetado quando a licença permitir e verificar tamanho de build.
- [Grade variada causa layout shift] → devolver dimensões e reservar `aspect-ratio` antes do carregamento.
- [Pagamentos com muitos registros] → filtros/paginação server-side, agregação em lote e índices apenas se o plano de consulta demonstrar necessidade.
- [Estado de pagamento diverge do acesso] → badges separados e enumerações calculadas pelo backend com testes de precedência.
- [Resumo abre UUID manipulado] → validar o parâmetro contra a lista autorizada antes de consultar a pasta.

## Migration Plan

1. Adicionar propósito de pasta e backfill `content`, sem mudar estado, posição, fotos ou referências existentes; criar pastas técnicas somente sob demanda.
2. Publicar contratos compatíveis de capa, dimensões, agregados e publicação incremental antes de trocar os consumidores.
3. Migrar o editor: Vendas, capa na etapa 03, organização/publicação na etapa 04 e ações de cliente na etapa 05.
4. Migrar resumo, Pagamentos e apresentação compartilhada, mantendo leitura compatível dos payloads anteriores durante o mesmo deploy.
5. Validar migrations do zero/sobre o head, API, worker, frontend, acessibilidade e ausência de N+1; usar somente JPEGs e identidades sintéticos.
6. Antes de homologação, apresentar inventário zero-impact, backup e migration aditiva para autorização específica. Depois do deploy, confirmar Alembic head, healthchecks e roteiro humano desktop/mobile.

Rollback de aplicação preservará a coluna/pasta técnica aditiva e os dados publicados. A versão anterior não deverá receber upload adicional em pasta `released`; durante rollback essa ação fica desabilitada. Não haverá downgrade ou limpeza física automática em homologação sem nova autorização.
