## Why

A revisão humana em homologação mostrou que o sistema ainda concentra quase todas as páginas em containers estreitos e mantém escolhas de capa duplicadas que carregam desnecessariamente o acervo. A jornada da cliente também apresenta uma ação de avanço sem texto visível e mistura a capa editorial com a revisão das fotos selecionadas, reduzindo clareza e aproveitamento da tela.

## What Changes

- Adotar um sistema de layout compartilhado full-width, fluido e responsivo para todas as superfícies administrativa, cliente e autenticação, com gutters adaptativos e limites de leitura aplicados somente a textos longos ou formulários que realmente precisem deles.
- Corrigir primeiro os shells e wrappers globais que hoje limitam `admin-shell`, `admin-content` e `client-content`, eliminando a necessidade de exceções de largura por página.
- Fazer cards, grids, listas, galerias e mídias usarem a área útil disponível e reorganizarem colunas de forma responsiva, sem distorcer imagens nem criar overflow horizontal.
- **BREAKING**: remover da etapa 03 a escolha de capa entre fotos das pastas; a capa será enviada exclusivamente do dispositivo para o pipeline técnico de capa, sem listar o acervo de conteúdo.
- Fazer a capa enviada tornar-se a capa vigente assim que seu derivado estiver pronto, preservando tipografia, cor, tamanho, posição, prévia e possibilidade de substituição por novo upload.
- Remover da etapa 04 a ação `Usar como capa`/`Capa atual` de cada foto, mantendo ampliação, seleção administrativa, exclusão e estados de processamento/publicação.
- Tornar inequívoco o CTA flutuante da cliente com texto visível `Prosseguir`, contraste e nome acessível em todos os estados.
- Na revisão/checkout da seleção, mostrar somente as fotos escolhidas e os dados comerciais, sem renderizar a capa da galeria como item concorrente.
- Integrar comentários ao contexto de cada foto ampliada, abaixo da mídia, em vez de exigir um seletor global de foto separado da visualização.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `gallery-sales/original-gallery-experience`: todas as páginas e componentes passam a obedecer ao sistema de layout fluido e responsivo, com fotografia e dados operacionais usando a área útil da viewport.
- `gallery-sales/operational-gallery-interface`: Detalhes passa a aceitar somente upload dedicado de capa e Imagens deixa de oferecer fotos de conteúdo como candidatas a capa.
- `client-access/derived-galleries`: a seleção da cliente recebe CTA textual inequívoco, revisão sem capa editorial e comentários vinculados à foto ampliada.

## Impact

- CSS global, tokens de layout, shells administrativo/cliente, página de autenticação, componentes compartilhados de página, cards, grids, diálogos e media queries.
- Editor administrativo nas etapas 03 e 04, contrato FastAPI de detalhes/capa e testes de integração do pipeline de mídia.
- Galeria pública/privada, barra flutuante, revisão/checkout, visualizador compartilhado e comentários por foto.
- Testes frontend de componentes e rotas, testes backend de capa, lint, typecheck, build e validação visual desktop/tablet/mobile.
- Não há migration prevista, alteração de permissões, exposição de originais, mudança de preços ou ativação de integração externa.
