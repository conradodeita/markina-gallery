## Why

A revisão humana em homologação mostrou que o backend já suporta parte relevante do fluxo comercial, mas a interface ainda oculta Vendas, acopla a publicação de pastas a galerias privadas e obriga o fotógrafo a saltar entre etapas para configurar a capa. O resumo, Pagamentos e a apresentação fotográfica também não oferecem a hierarquia visual e as ações operacionais necessárias para testar o ciclo completo com segurança.

## What Changes

- Ativar a etapa 02 **Vendas** com os contratos existentes de faixas de preço, PIX manual, texto comercial, prazo e interações, sem confirmar pagamento automaticamente.
- Permitir na etapa 03 enviar uma imagem de capa própria ou escolher uma foto já existente, selecionar a capa e visualizar imediatamente título, posição e tipografia sobre a imagem.
- Ampliar a lista segura de tipografias do título com famílias editoriais e manuscritas empacotadas localmente, com fallback, licença e sem dependência de terceiros em runtime.
- Mover **Organização das pastas** de Detalhes para a etapa 04 **Imagens e pastas**.
- **BREAKING**: remover da etapa 04 a seleção de destinos “Liberar para galerias privadas”. A publicação passa a declarar que a pasta ou as novas fotos estão disponíveis na Galeria pública conforme o modo de acesso; fotos privadas continuam sendo escolhidas por cliente na etapa 05 ou pela seleção da própria cliente.
- Permitir adicionar fotos a uma pasta já publicada sem ocultar as fotos anteriores: os novos arquivos permanecem administrativos durante processamento/revisão e são publicados explicitamente depois de prontos.
- Corrigir e testar de ponta a ponta **Desvincular cliente** e **Disponibilizar fotos**, com estados, motivos de bloqueio, progresso e atualização do card orientados pelo backend.
- Transformar o resumo da Galeria pública em superfície operacional: miniatura de capa por pasta, abertura da pasta para visualizar/adicionar/excluir fotos e cards reutilizáveis de clientes com selecionadas, compradas, estado da galeria e situação de pagamento/prazo.
- Criar um painel de Pagamentos agrupado por cliente, com resumo, cards coloridos e textuais, filtros recolhíveis por cliente, galeria, período, situação financeira e entrega de mensagem, além das ações atuais de decisão e reenvio.
- Refinar a apresentação compartilhada do fotógrafo e da cliente para uma galeria editorial, sem molduras de card sobre as fotos, com espaçamento uniforme, adaptação às proporções horizontal/vertical, responsividade e marcador visível de favorito/seleção no papel da cliente.
- Manter prévias autenticadas, limitadas e marcadas pelo servidor; a reorganização visual não expõe originais nem promete impedir screenshots.

## Capabilities

### New Capabilities

- `gallery-sales/payment-operations-dashboard`: controle administrativo de pagamentos e notificações agrupado por cliente, com filtros, estados visuais, decisão manual e retomada de mensagens.

### Modified Capabilities

- `gallery-sales/operational-gallery-interface`: completar Vendas, antecipar a gestão de capa, reorganizar Imagens, corrigir ações de clientes e tornar o resumo da Galeria pública realmente operacional.
- `gallery-sales/original-gallery-experience`: elevar a composição compartilhada do fotógrafo e da cliente, preservando ações e dados específicos de cada papel.
- `gallery-visualization-and-watermark-controls`: ampliar tipografias controladas, mover a organização para Imagens e adaptar a grade às proporções das fotos com indicador de favorito/seleção.
- `media-storage/staged-folder-release`: publicar conteúdo para a Galeria pública sem escolher galerias privadas e permitir novas rodadas dentro da mesma pasta sem expor arquivos ainda em preparação.

## Impact

- Frontend Next.js: editor em cinco etapas, resumo da Galeria pública, gestão contextual de pasta, painel de Pagamentos, composição compartilhada da galeria, design tokens e testes responsivos/acessíveis.
- Backend FastAPI: contratos de capa antecipada, publicação incremental, resumo de pasta/cliente, situação comercial agregada e filtros/paginação de pagamentos; reaproveitamento das regras atuais de preço, PIX, ciclo de vida e mensageria.
- Banco e mídia: migration aditiva apenas se necessária para distinguir o acervo técnico de capa; nenhuma duplicação de foto por cliente, nenhuma alteração de histórico comercial e nenhuma migration destrutiva.
- Assets: fontes locais com licença versionada, sem chamadas externas no navegador.
- Homologação: nova revisão humana com dados sintéticos nos cinco passos, resumo, Pagamentos e apresentação em desktop e smartphone; deploy continua sujeito a inventário e autorização explícita.
