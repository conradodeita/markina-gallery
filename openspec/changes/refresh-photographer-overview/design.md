# Design

## Context

Referência visual aprovada no Google Stitch: projeto Pick your Pic — Visual Redesign `14942044356996446740`, tela Visão Geral Dourado Claro `5e4c66ed48ca4027b89852acba9d7018`. A variante escura `57bdcac29d814bd48c3c3e6ff6a44bec` orienta a paleta correspondente. A composição usa barra lateral de 264 px, cabeçalho de 64 px, fundo contínuo quente, corpo com cinco métricas em 3+2, três etapas de publicação e cartões recentes em pares. No celular, navegação recolhível e conteúdo em uma coluna.

## Goals / Non-Goals

Reconstruir a composição da rota `/admin` e manter seus fluxos autenticados. Reutilizar a estrutura visual nas listas de Galerias e Clientes, em Vendas e pagamentos e no formulário inicial de Nova galeria. Preservar aparência, sessão e links com permissões existentes. Edição de galerias, upload, cliente móvel e checkout mantêm suas interfaces até seus incrementos.

## Decisions

- Encapsular a composição em um módulo CSS, com Plus Jakarta Sans e subconjunto de Material Symbols distribuídos localmente e acompanhados das licenças OFL e Apache 2.0. A estrutura reutiliza a navegação administrativa, a sessão e as variantes de aparência. O filtro do cabeçalho leva à busca existente em Galerias; a Visão Geral não introduz índice global.
- Priorizar a sequência hero, indicadores, prática de publicação, galerias, seleções e carteira. Preservar as cinco métricas já oferecidas pela aplicação e manter a carteira após a operação recente.
- Preservar os destinos reais dos links, as permissões de console e monitor, as notificações da sessão e a saída. O tema completo continua disponível junto ao perfil. O instalador mantém uma única instância global, apresentada como ação flutuante quando disponível nas rotas com a navegação Dourado Claro.
- Usar aparência sem capa para as galerias recentes. A projeção atual não fornece capa, imagem ou data da galeria. A composição não cria solicitação por cartão e não incorpora dados, capas ou ações demonstrativas do protótipo.

### Mapa tela, resposta e estados

| Região | Origem e campos | Estado e ação |
| --- | --- | --- |
| Admissão ao painel e sessão | `GET /api/auth/destination` (`destination`) e `GET /api/auth/identity` (`role`, `identity`) pelos componentes existentes | Redirecionamento e escopo seguem a sessão atual. O menu de conta carrega a identidade autorizada. |
| Endereço da marca | `GET /api/admin/onboarding/address` (`base_domain,hostname,state,choice_complete,suggested_prefix,public_url`) pelo aviso existente | Escolha pendente ou erro de consulta aparecem no aviso próprio. Conta com escolha concluída mantém a tela livre do aviso. |
| Indicadores operacionais | `GET /api/admin/validation-summary` · `counts.parent_galleries`, `clients`, `folders_with_active_imports`, `photos_in_folders_with_active_imports`, `folders_released`; `storage.photo_count`, `bytes`, `available` | Carregamento e erro do resumo; armazenamento indisponível quando a medição não responde. |
| Galerias recentes | Mesmo resumo · `recent_galleries[].id,name,active,event_name` | Lista vazia ou cartões com estado ativo/bloqueado e link para `/admin/galleries/sources/{id}`. A projeção não inclui capa. |
| Seleções em andamento | Mesmo resumo · `recent_selections[].scope_id,client,gallery,parent_gallery,selected_count,selection_started_at`; a resposta inclui `last_selected_at`, sem renderização no cartão | Lista vazia ou seleção com horário local e atalho à seleção correspondente em Vendas e pagamentos. |
| Carteira e movimentações | `GET /api/admin/credits/wallet` · `wallet.mode,available_credits,reserved_credits,pending_operations,recent_consumed_credits,recent_period_days,can_upload_content`; `entries[].id,type,delta,source_reference,description,created_at` | Carregando, disponível, ilimitado, sem movimentações, saldo insuficiente ou indisponível. A falha da carteira preserva indicadores e atalhos do resumo. |
| Prática e ações de publicação | Dicas fixas, URLs `/admin/galleries` e `/admin/galleries/new` | Criação e consulta usam rotas existentes. A busca direciona ao filtro da lista, que consulta `GET /api/admin/parent-galleries/overview?query=...`. |

### Catálogos administrativos

- Galerias Dourado Claro `7938e6b20cd54c78af6773376d61d555`: composição com título e ação Criar galeria, resumo, busca e catálogo em grade ou lista. Exibir galerias públicas retornadas pelo catálogo. O contador de resultados vem de `total`; vínculos, cadastros e estado de cada cartão vêm da galeria correspondente. Somatórias auxiliares indicam que se referem aos resultados exibidos. O estado «Sem capa» acompanha a ausência de `cover_preview_url`. As galerias privadas continuam acessíveis no espaço de cada galeria pública, onde já são operadas.
- Clientes Dourado Claro `490cf547c6e248cba09f80f5d1563c5f`: composição com título, atalho de cadastro, busca e registros alinhados em colunas no desktop. A apresentação móvel empilha os dados. Os indicadores da lista consideram somente clientes carregadas e são identificados como tal. A edição e o cadastro usam os formulários existentes. Última atividade, exportação e filtros demonstrativos do protótipo exigem contratos próprios e ficam fora deste recorte.

| Região | Origem e campos | Estados e ações |
| --- | --- | --- |
| Galerias | `GET /api/admin/parent-galleries/overview?query=...` · `total`, `parent_galleries[].id,name,event_name,active,cover_preview_url,private_gallery_count,registration_count` | Carregamento, erro, nenhum resultado, cartão com ou sem capa e situação ativa/bloqueada. Busca por nome, evento, cliente ou telefone; alternância de grade/lista usa os mesmos resultados. Criação e detalhe mantêm suas rotas e autenticação. |
| Clientes | `GET /api/admin/clients?limit=24&query=...&cursor=...` · `clients[].id,name,phone,aggregates.public_galleries,aggregates.private_galleries,aggregates.orders,deletion_eligible`, `page.has_more,next_cursor` | Carregamento, erro, nenhum cadastro, nenhum resultado ou resultados com e sem vínculo. Busca por nome ou WhatsApp, paginação e edição mantêm o comportamento existente. |
| Ações de cliente | `POST /api/admin/clients`, `PATCH /api/admin/clients/{id}`, endpoints de alteração de telefone e inventário/exclusão usados por `ClientEditorDialog` | Cadastro, edição e exclusão continuam delegados aos componentes atuais, com os mesmos controles de autorização e confirmação. |

### Ajuste de leitura no tema claro e no editor

- O tema claro aproxima o fundo do branco e mantém superfícies, controles e estados destacados. O fundo escuro aproxima-se do preto, com cartões e controles em um nível distinto.
- O editor de cliente cabe na janela e rola quando seu conteúdo ultrapassa a altura disponível. A página de fundo conserva a posição enquanto o editor está aberto, incluindo quando inventário ou erro acrescentam conteúdo ao diálogo.

### Vendas e pagamentos

- Referência Dourado Claro `f9bc42a74c3043db91f3a014f6f8f850`: título e modo de exibição, aviso de verificação manual, resumo financeiro, filtros e resultado agrupado. A UI usa o layout da referência e os valores do filtro atual. Métricas de demonstração e registro manual sem contrato correspondente ficam fora deste recorte.
- O resultado mantém grupos por cliente com pedidos e seleções. Os cartões preservam decisões financeiras protegidas, liberações, confirmações e mensagens. O CSV usa o filtro que gerou a lista.

| Região | Origem e campos | Estados e ações |
| --- | --- | --- |
| Pedidos, resumo, filtros e seleção | `GET /api/admin/payment-communications` · `summary`, `facets`, `groups`, `templates`, `selections_without_order`, `page.next_cursor` | Prioridades, busca, filtros, paginação e seleção por link direto. Carregamento, erro, nenhum resultado e lista carregada. |
| Clientes para filtro e exportação | `GET /api/admin/clients?query=...` e `GET /api/admin/payment-communications/export.csv` | Busca depende dos dados da conta; exportação reutiliza os filtros aplicados e mantém estados de sucesso/erro. |
| Reabertura e ações do pedido | `GET /api/admin/gallery-reopening-requests`, `POST /api/admin/payment-communications/{id}/{decision\|correction}` e `/api/admin/orders/{id}/delivery` | Decisão autorizada, repetição de notificações e ações financeiras permanecem nos componentes e contratos atuais. |
| Histórico de acervo excluído | `GET /api/admin/removed-photo-movements` no componente `RemovedHistory` | O histórico mantém filtros, paginação e comprovantes autorizados. |

### Nova galeria

- Referência Dourado Claro `b8b084ff16534752a299c6789f6d2e55`: link de retorno, cabeçalho editorial e formulário com três campos e ações. Os temas claro e escuro usam os tokens das outras telas do fotógrafo.
- `POST /api/admin/parent-galleries` recebe `name`, `event_name` e `description`, com `null` para opcionais vazios. A interface usa somente `id` da resposta para seguir ao editor existente em `/admin/galleries/sources/{id}/edit/ajustes`. A autenticação, a criação e a emissão de acesso continuam com o endpoint atual.
- A interface apresenta validação nativa do título, envio em andamento, rejeição e erro de resultado incerto. Um envio em andamento aceita uma única solicitação. Campos são preservados após erro. Em resultado incerto, a mensagem orienta conferir o catálogo antes de reenviar.

### Notificações

- Referência Stitch `97c1495c2c88493f8fd77537eb577d58`: cabeçalho, faixa de informações sobre os canais, controle por destinatário e eventos expansíveis. Mostrar o estado de WhatsApp fornecido pela API. Indicadores de volume e conexões demonstrativas ficam fora deste recorte.
- `GET /api/admin/notification-settings` fornece `settings` e `whatsapp_editable`. A UI usa `recipient` para selecionar eventos de fotógrafo ou cliente e preserva edições ainda não salvas ao alternar o filtro. Deep links existentes podem abrir o evento correspondente.
- `PUT /api/admin/notification-settings/{event_type}` mantém `version`, habilitação e textos de cada canal, inclusive bloqueio do WhatsApp sem conexão, conflito e erros. A prévia substitui as variáveis de forma local, sem envio.
- A central de mídia fria mantém os contratos `GET /api/admin/media-archive/notices?limit=50` e `POST /api/admin/media-archive/notices/{id}/read`, com o mesmo vínculo às pastas e estados de leitura.

### Tabelas de preço progressivo

- Referência Stitch `05c0a1e7df4f471e8bc4d8c88b2fd58c`: título com atalho de criação, explicação da progressão, resumo do catálogo e cartões junto ao editor. A interface usa contagens do catálogo carregado. Indicadores demonstrativos de conversão e uso por galeria ficam fora do recorte.
- `GET /api/admin/pricing-presets?include_inactive=true` fornece `presets[].id,code,name,label,version,active,tiers`; os cartões mostram valores em reais, versão e disponibilidade. O resumo indica tabelas ativas, desativadas e total do catálogo.
- O editor envia `code,name,tiers[].minimum_quantity,maximum_quantity,unit_price_cents` no `POST /api/admin/pricing-presets` ou `PUT /api/admin/pricing-presets/{id}`. As regras de faixas e centavos continuam existentes. `DELETE /api/admin/pricing-presets/{id}` e `POST /api/admin/pricing-presets/{id}/activate` mantêm os comportamentos de desativação confirmada e reativação.

### Configurações

- Referência Stitch `f1c9d2ab81c145d8becd18f35f96b4e2`: cabeçalho do estúdio, cartões por assunto com ícones e edição da marca com prévia ao lado no desktop. A UI mantém os sete grupos que a aplicação oferece, a prévia da entrada após salvar e a prévia local da marca-d’água.
- `GET /api/admin/branding` carrega identidade, ativos e proteção. `PATCH /api/admin/branding`, `PUT /api/admin/branding/{asset}` e `PATCH /api/admin/branding/protection` mantêm textos, arquivos e campos existentes. O estado de carregamento, erro ou resposta salva continua visível.
- Endereço, termos, segurança, WhatsApp, PIX, provedores e encerramento permanecem nos componentes atuais, com as mesmas permissões e endpoints. Atalhos internos e links externos como `#pix` e `#whatsapp` mantêm seus destinos.

### Resumo da Galeria pública

- Referência Stitch `4cf26c3c9f7f4fde986239056bb8d0b7`: caminho de volta ao catálogo, cabeçalho com ações, capa autorizada, indicadores e pastas em cartões. O resumo usa nome, evento, link protegido e contagens da API. Estatísticas demonstrativas de seleção, datas e resolução não são apresentadas como dados.
- `GET /api/admin/parent-galleries/{id}/summary` fornece `name,event_name,cover_preview_url,public_link_status,counts,clients,deletion_operation`. `GET /api/admin/parent-galleries/{id}/folders` fornece `id,name,status,photo_count,preview_url,media_state,access_expires_at` de cada pasta. Se a capa não está disponível, a superfície informa seu estado.
- A busca local procura nome ou telefone entre as clientes autorizadas retornadas. Prévia, ajustes, imagens, clientes, pastas e inventário/andamento da exclusão mantêm rotas, permissões e confirmações atuais.

### Pedidos da galeria

- Referência Stitch `85a405cea370449585c8e2f1314507e0`: cabeçalho, resumo, aviso de preservação dos snapshots, busca por cliente ou ID e cartões de pedidos. Contagens são calculadas sobre a resposta autorizada; o total confirmado soma somente o subtotal de cada pedido confirmado nesta galeria.
- `GET /api/admin/derived-galleries/{id}/orders` fornece `orders[].id,payment_status,cart_reopened_at,total_cents,payment_group,client_name,created_at,price_rule,sales_message,pix,items`. Busca e filtros usam a lista carregada; a consulta é somente leitura. Confirmação, CSV e entrega continuam no fluxo de Vendas e pagamentos.

### Ajustes da galeria

- Referência Stitch `c7d92f1bd8874527932cb7c91733ed17`: cabeçalho, prévia, trilha de etapas, identificação e bloco de acesso. A primeira etapa usa as permissões e as opções reais, inclusive o estado protegido legado. As demais etapas continuam com seus próprios formulários.
- `GET /api/admin/parent-galleries/{id}/editor` fornece `gallery.name,event_name,description,active,access_mode` e `steps[].id,label,status,available`. O controle mantém `PATCH /api/admin/parent-galleries/{id}/settings`, avanço somente após sucesso, estados de salvamento e confirmação existente ao sair com mudanças.

### Vendas da galeria

- Referência Stitch `16f4e7e2a7084819b60ab22b353eeb8e`: trilha do editor, escolha de precificação, simulação, PIX somente leitura e jornada da cliente. As opções são as existentes, com valores e disponibilidade da API.
- `GET /api/admin/parent-galleries/{id}/sales` e `GET /api/admin/pricing-presets` fornecem a configuração e as tabelas ativas. `GET /api/admin/pricing-presets/{id}/quote?quantity=...` calcula a prévia do preço progressivo. O `PUT /api/admin/parent-galleries/{id}/sales` mantém centavos, modo, tabela selecionada, conversão legada, exigência de pagamento, mensagem e preferências. Nenhum pagamento é realizado nessa etapa.

### Detalhes e apresentação da galeria

- Referência Stitch `7cb288945dd54e928e4b243248b75574`: trilha do editor, prévia da capa em destaque e controles de imagem e título. A fotografia vem da capa autorizada, sem ativos de demonstração nem filtros de cor. Os controles existentes determinam fonte, cor, posição e tamanho da prévia.
- `GET /api/admin/parent-galleries/{id}/details` fornece `cover_readiness,font_options,cover_options,settings`. O fluxo mantém as operações existentes de upload JPEG e processamento. A etapa avança após salvar os ajustes com capa pronta e mantém os estados de capa ausente, processando ou com falha.

## Risks / Trade-offs

O cabeçalho e a navegação aparecem em tamanhos diferentes conforme a janela, com um único menu de navegação ativo e foco visível. Sem resumo autorizado disponível a estrutura visual permanece acessível, e o conteúdo informa carregamento ou erro. Preferências de movimento reduzido e tema são preservadas.
