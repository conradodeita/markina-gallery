# Design

## Context

Veja `proposal.md` e os contratos delta. `/admin/validation-summary` já fornece galerias recentes por tenant; `/admin/payment-communications` já retorna grupos de seleções atuais e aceita `client_id` e `parent_gallery_id`. A tela de pagamentos, porém, ignora parâmetros de URL e começa com o filtro prioritário. `PhotoSelection` é o estado atual do carrinho; o checkout o remove quando congela/finaliza a seleção. `NotificationMilestone(first_selection)` é um marco único e linhas baseline de clientes já vinculadas podem impedir novos marcos, portanto não é uma fonte confiável de atividade atual.

## Goals / Non-Goals

**Goals:**

- Projetar atividade atual com os dados já persistidos, isolada por tenant.
- Reutilizar filtros, grupos “No carrinho” e cartões financeiros existentes.
- Preservar galerias recentes, navegação, pagamentos e seleções sem alterar seu ciclo de vida.

**Non-Goals:**

- Guardar histórico de seleções encerradas, criar evento/tabela ou alterar `NotificationMilestone`.
- Recalcular preços, pedidos, saldo, prazo, pagamentos ou notificações.
- Remover a lista de galerias recentes ou refatorar o agrupamento financeiro existente.

## Decisions

### 1. `PhotoSelection` será a fonte da lista

O resumo usará as seleções que ainda existem, agrupadas pelo mesmo escopo efetivo usado em Vendas e pagamentos e pela cliente. Para compatibilidade com linhas antigas, o escopo será a galeria derivada quando presente ou a Galeria pública canônica nos demais casos; o identificador da Galeria pública também será retornado para o filtro e a autorização já existentes. A consulta SHALL filtrar por `tenant_id` antes de agregar.

Cada grupo fornecerá quantidade atual e atividade mais recente a partir de `PhotoSelection.created_at`; a lista será ordenada por essa atividade e limitada a cinco grupos. O instante de início virá de um novo campo opcional `selection_started_at` em `GalleryClientState`, a identidade já existente para o par Galeria pública/cliente. Ao incluir a primeira foto quando não houver seleção atual, o serviço definirá `now()`; inclusões seguintes preservarão o valor. Quando o carrinho estiver vazio, ele não aparece na lista; a próxima inclusão define o início da nova sessão. Não se alterará `NotificationMilestone` nem se criará evento duplicado.

Carrinhos já ativos antes desta mudança podem não ter início exato recuperável. A migration SHALL deixar o campo nulo nesses casos, sem reconstruir horários; a interface SHALL indicar “Horário não registrado”, sem inferir o instante a partir da primeira foto restante. Novos inícios passam a ser registrados daqui em diante.

**Alternativa considerada:** reaproveitar a resposta completa de `/admin/payment-communications` na Visão geral. Foi rejeitada porque a rota também monta pedidos, comunicações, preços e nomes de fotos, gera uma carga maior que o resumo precisa e não limita os grupos de seleção. A projeção do resumo será compacta e não alterará a rota operacional.

### 2. O atalho reutilizará filtros e cartões de Vendas e pagamentos

O link incluirá `client_id` e `parent_gallery_id`; o fragmento de URL identificará a linha específica de seleção pelo escopo efetivo e cliente. Quando ambos os filtros vierem do atalho, a tela iniciará com situação `Todas` (parâmetro financeiro ausente), preservando o filtro prioritário para navegação normal. Depois da resposta existente, a interface tentará focar a seleção; se ela tiver desaparecido, focará o cartão financeiro do cliente. A API continuará validando o administrador e aplicando o tenant da requisição.

**Alternativa considerada:** adicionar um endpoint dedicado ou uma rota para cada cliente. Foi rejeitada porque os filtros atuais já expressam o destino e evitam um novo contrato, endpoint ou regra de autorização.

### 3. O cartão de galerias permanece

A nova lista será adicionada ao card “Acesso recente” sem remover ou substituir os atalhos de galerias recentes, comportamento já coberto por uma change existente. Isso mantém os destinos que o fotógrafo já usa e evita uma regressão funcional não solicitada.

### 4. Horários sem histórico exato ficam explícitos

A migration adicionará somente uma coluna nullable em `GalleryClientState`, sem backfill que transforme uma estimativa em horário exato. Carrinhos iniciados antes da captura não terão horário até serem esvaziados e uma nova seleção começar. Esse tratamento inclui registros legados sem estado canônico.

### 5. Exibição de fuso horário

O banco e a resposta da API preservam o instante em UTC. O produto ainda não tem uma preferência de fuso por tenant; por isso, o painel formata o instante no fuso local do dispositivo do proprietário e informa isso junto à lista. A exibição não afirma representar um fuso cadastrado do tenant. Uma futura configuração de fuso por tenant exigirá comportamento de produto próprio.

## Risks / Trade-offs

- [Linhas antigas usam galeria derivada como escopo] → agrupar pela mesma chave efetiva do painel de pagamentos e carregar também a Galeria pública canônica para o filtro.
- [A seleção muda entre o resumo e o clique] → recarregar pelo backend; preferir a linha atual e usar o cartão financeiro como fallback, sem estado simulado.
- [Agregação em tenants com muitos itens] → retornar apenas cinco grupos e limitar a consulta ao tenant. Só considerar índice adicional se validação de consulta demonstrar necessidade; a única migration prevista é a coluna nullable de início.
- [Uma seleção encerrada deixa de aparecer] → documentar o alcance como carrinho atual, não histórico de atividade.

## Migration Plan

Sem nova tabela ou alteração de pedidos. A migration será aditiva, com uma coluna nullable sem preenchimento histórico inventado. Reverter a funcionalidade local não exige alterar dados financeiros ou mídia. Qualquer publicação remota continua fora do escopo e depende de autorização separada.
