## Context

Consulte `proposal.md` e os seis delta specs desta change. Hoje `PhotoAsset` e `PhotoFolder` pertencem obrigatoriamente a uma Galeria pública; uma privada contém somente referências a esses ativos. A confirmação financeira é uma decisão sobre `PaymentCommunication`, os templates são globais, `/admin/payments` já contém o fluxo de decisão e `/admin/purchases` apresenta outra visão comercial. Os agregados administrativos são calculados por consultas separadas e as telas de galeria os carregam apenas na abertura.

O roadmap exige carrinho e pedido separados por cliente e galeria, snapshots imutáveis, confirmação manual, histórico após expiração, mídia protegida e operações auditáveis. A mudança deve preservar fotos públicas e referências privadas existentes, sem converter ou apagar mídia durante a migration.

### Reconciliation with active changes — 2026-09-09

- `add-payment-confirmation-notifications` permanece autoridade para comunicação, decisão, templates e outbox; esta change amplia sua operação com correção append-only e uma superfície contextual, sem permitir confirmação antes da comunicação.
- `improve-gallery-and-client-data-lifecycle` permanece autoridade para exclusão, desvinculação, preservação comercial e links; mídia privada nova entra no mesmo inventário e nunca reduz seus gates.
- `consolidate-shared-private-galleries-and-progressive-sales` permanece autoridade para membros compartilharem acervo e manterem interações individuais; esta change substitui apenas a montagem administrativa por catálogo público por upload próprio da privada.
- `productionize-facial-search` permanece autoridade para fila, modelo, gates e busca pública; esta change adiciona escopo privado aos jobs/índices e proíbe seu consumo por busca pública.
- `expand-fluid-layout-and-simplify-gallery-flow` permanece autoridade visual para layout fluido, capa dedicada e revisão da cliente; os novos componentes SHALL reutilizar esses wrappers e não restaurar seletores de capa ou containers estreitos.

Não existe proposal ativa com autoridade para confirmar pagamento sem comunicação, reutilizar foto privada em outra galeria ou reabrir prazo por membro. Em qualquer sobreposição, os requisitos mais restritivos de privacidade, histórico e autorização continuam prevalecendo.

### Technical inventory — 2026-09-09

- Persistência principal: `backend/app/auth.py` (`PhotoFolder`, `PhotoAsset`, `DerivedGallery`, `DerivedGalleryPhoto`, `PhotoSelection`, `SaleOrder`, `SaleOrderItem`, `PaymentCommunication`, `PaymentNotificationOutbox`).
- Produção de mídia: endpoints de pasta/upload em `backend/app/main.py`; derivados e fila em `backend/app/worker.py`; armazenamento e remoção em `backend/app/gallery_cleanup.py`, `gallery_lifecycle.py` e `private_gallery_lifecycle.py`.
- Facial: `backend/app/facial/jobs.py`, `engine.py`, `status.py`, `search.py`, `search_worker.py`, `purge.py` e workers. Consultas atuais usam `parent_gallery_id`, portanto precisam de filtro explícito de escopo público.
- Seleção e checkout: `private_derivation.py`, rotas `/public-galleries/.../selection`, `/gallery/.../selection`, carrinho e checkout em `main.py`; todas convergem em `PhotoSelection` e `SaleOrder` por privada/cliente.
- Financeiro e mensagens: rotas `/gallery/.../payment-communications`, `/admin/payment-communications/.../decision`, `/admin/payment-communications`, templates globais e worker/outbox em `main.py`, `payment_templates.py`, `messaging.py` e `worker.py`.
- Agregados: `/admin/parent-galleries/{id}/clients`, `/admin/derived-galleries/{id}/members`, seleção individual e dashboard financeiro em `main.py`; hoje usam subqueries independentes.
- Interfaces afetadas: ficha privada e seleção/pedidos em `frontend/app/admin/galleries/[galleryId]/`, cards compartilhados e etapa Clientes, `/admin/payments`, `/admin/purchases`, Configurações, galeria pública/privada da cliente e biblioteca.
- Migrations ficam em `backend/migrations/versions`; a nova revision deve partir do único head vigente e ser apenas aditiva para o rollout normal.

## Goals / Non-Goals

**Goals:**

- Introduzir propriedade privada explícita sem duplicar o pipeline de mídia.
- Tornar contadores e estados comerciais projeções autoritativas reproduzíveis.
- Reunir seleção, pedido, pagamento e entrega de mensagem numa operação administrativa contextual.
- Permitir reabertura e correção financeira com histórico e idempotência.
- Preservar compatibilidade de URLs e dados existentes durante rollout e rollback.

**Non-Goals:**

- Migrar automaticamente referências públicas existentes para propriedade privada.
- Permitir reutilização de mídia privada entre galerias ou pesquisa facial cruzada.
- Confirmar pagamentos sem comunicação da cliente, conciliar extrato bancário ou integrar um provedor de pagamento.
- Enviar mensagem para correção financeira ou decisão de reabertura da cliente nesta entrega.
- Implementar estorno contábil, reembolso ou apagar uma decisão financeira histórica.

## Decisions

### 1. A propriedade privada estende o agregado de mídia existente

`PhotoFolder` e `PhotoAsset` ganharão escopo e proprietário privado opcionais, mantendo `parent_gallery_id` como linhagem do evento e contexto comercial. Uma pasta de conteúdo terá escopo público ou pertencerá a exatamente uma `DerivedGallery`; suas fotos herdarão esse proprietário e constraints impedirão divergência. Fotos privadas continuarão no pipeline e nas tabelas de derivados existentes, mas somente o proprietário privado poderá receber sua referência.

Essa abordagem preserva worker, proteção, armazenamento, deduplicação interna e lifecycle. Criar tabelas paralelas duplicaria processamento e consultas; tornar `parent_gallery_id` nulo quebraria a coerência de evento, preços e grande parte das autorizações. O vínculo de linhagem não concede visibilidade pública.

Registros atuais permanecem públicos e suas referências derivadas continuam válidas. O fluxo de seleção da cliente na Galeria pública ainda pode manter a foto selecionada em sua privada; o que desaparece é a montagem administrativa por catálogo público. Novos uploads administrativos da privada sempre usam pasta privada e não aceitam IDs existentes. As rotas administrativas legadas de criação com `photo_ids`, inclusão de fotos e clonagem de referências recusam novas gravações; leitura e remoção de justificativas `admin` já persistidas permanecem disponíveis para compatibilidade e limpeza segura.

### 2. Índices e métricas faciais carregam o mesmo escopo da foto

Jobs e índices de fotos privadas registram o identificador da privada. O reconciliador, as métricas e a busca aplicam o escopo de origem: índice privado nunca entra no snapshot de uma busca pública. A change entrega processamento e cobertura administrativa da privada; não cria uma nova pesquisa facial da cliente dentro da privada.

Alternativa descartada: indexar a foto privada no snapshot da Galeria pública por compartilhar `parent_gallery_id`; isso ampliaria conteúdo autorizado e violaria a propriedade exclusiva.

### 3. Uma projeção comercial comum alimenta todas as superfícies

O backend terá uma consulta/projeção compartilhada por `parent_gallery_id`, `derived_gallery_id` e `client_id`. Ela contará:

- acervo privado: fotos atualmente visíveis naquela privada, sejam referências válidas por seleção ou ativos próprios;
- selecionadas: seleções vigentes daquela cliente e privada;
- compradas: fotos distintas em pedidos confirmados daquela cliente e galeria;
- estado: seleção sem pedido, aguardando pagamento, comunicado, confirmado, não localizado, expirado ou reabertura solicitada.

Na área financeira, os valores serão projetados em três conjuntos mutuamente exclusivos. Seleções persistidas ainda não comunicadas formam o valor atual do carrinho pela cotação vigente, inclusive quando já existe rascunho de checkout editável. Pedidos congelados cuja comunicação está em `pending_review` formam `Valor dos pedidos`. Somente pedidos em `payment_status=confirmed`, após decisão administrativa, formam `Receita confirmada`. Pedido recusado/cancelado não entra em nenhum dos três valores correntes e permanece disponível em seu estado histórico próprio.

Os endpoints da etapa Clientes, da ficha privada e da área financeira consumirão a mesma autoridade. Testes reproduzirão seleção real pelas rotas pública, privada e facial antes de consultar os dois cards. O frontend recarregará ao voltar ao foco e após mutações locais; não manterá contador derivado em armazenamento do browser.

Alternativa descartada: corrigir cada `COUNT` isoladamente. Isso manteria divergência entre telas e não cobriria transições posteriores.

Alternativa descartada: somar todo registro de `SaleOrder` como pedido financeiro. O checkout cria rascunho antes da comunicação e esse valor ainda é intenção editável, não receita nem pagamento comunicado.

### 4. `/admin/payments` torna-se a área canônica de Vendas e pagamentos

A implementação aproveitará o dashboard, filtros, decisão e retentativa já existentes em `/admin/payments`, ampliando sua consulta com seleções sem pedido, agrupamento de itens por pasta, reaberturas e links contextuais. A navegação terá uma única entrada `Vendas e pagamentos`; rotas antigas de Vendas/Compras serão preservadas como redirecionamento ou histórico especializado, sem duplicar ação financeira.

Cada ação recebe `communication_id` ou `reopening_request_id`, nunca apenas `client_id`, evitando decidir o pedido errado quando uma cliente compra em várias galerias. Os cards de galeria conduzem ao item filtrado; não confirmam um total agregado às cegas.

### 5. Confirmação e WhatsApp são transações independentes

A transação confirma a comunicação e o pedido, grava auditoria e outbox idempotente e atualiza a projeção. O commit financeiro acontece antes do consumo da outbox. Estado `failed` da entrega não altera o pedido e oferece retentativa conforme a política existente.

O template continua global. A ficha mostra seu texto e conduz à âncora de Configurações, com aviso de efeito global. A mensagem efetivamente enfileirada mantém o snapshot/render controlado já exigido pelo histórico.

### 6. Correção é uma revisão auditada, não edição destrutiva

Uma tabela append-only registra a correção com UUID da comunicação/pedido, administrador, decisão anterior, instante UTC e chave idempotente. Sob lock, o pedido `confirmed` volta a `pending`, a comunicação `confirmed` volta a `pending_review` e `confirmed_at` é limpo; pedidos em outros estados são recusados. A entrega de confirmação já ocorrida é preservada no histórico e nenhuma nova outbox é criada.

Agregados são calculados pelo estado corrente e deixam de contar os itens imediatamente. Uma nova confirmação posterior segue o mesmo endpoint de decisão e cria nova entrega com uma chave que incorpora a revisão, sem colidir com a confirmação anterior.

Alternativa descartada: apagar a decisão ou alternar booleano. Ambas perderiam autoria e impediriam compreender uma mensagem já enviada.

### 7. Reabertura é uma solicitação única por galeria

Uma entidade durável registra galeria, cliente solicitante, estado `pending | approved | refused`, data, decisão administrativa, novo prazo e chave de idempotência. Índice parcial/constraint lógica garante no máximo uma solicitação pendente por privada. Qualquer membro ativo pode solicitar após expiração, mas a decisão vale para a galeria inteira porque o prazo atual é compartilhado.

Ao aprovar, o backend exige uma data futura, atualiza `selection_expires_at` sob lock e libera novamente ações comerciais para todos os membros ativos. Ao recusar, conserva a expiração. O aviso ao fotógrafo usa a outbox WhatsApp genérica e falhas não afetam a solicitação. A cliente consulta o estado pela API da galeria.

Alternativa descartada: prazo por membro nesta change. Isso exigiria mover a autoridade de expiração para membership, reescrever carrinho e pedidos e contradiz a decisão aprovada de reabrir toda a galeria.

### 8. Expiração é aplicada no backend em todas as mutações comerciais

Seleção, remoção de seleção que altere carrinho aberto, checkout e finalização chamarão a mesma validação de prazo. Consultas continuam disponíveis e devolvem capability explícita para solicitar reabertura. A interface remove `Prosseguir` e exibe a mensagem e o botão definidos, mas não é a autoridade do bloqueio.

Alternativa descartada: desabilitar somente botões. Chamadas diretas ainda poderiam criar pedido após o prazo.

## Risks / Trade-offs

- [Nova propriedade de mídia amplia consultas e constraints] → migration aditiva, escopo explícito, índices compostos e testes PostgreSQL de isolamento antes do deploy.
- [Fotos públicas selecionadas e uploads privados coexistem na mesma privada] → expor origem somente ao admin e calcular visibilidade por uma projeção comum, sem transformar referência pública em propriedade privada.
- [Correção depois de mensagem enviada pode surpreender a cliente] → preservar entrega e auditoria, exigir confirmação administrativa explícita e não enviar mensagem adicional conforme decisão atual.
- [Reabertura por um membro afeta os demais] → informar o efeito no diálogo e manter prazo único já adotado pela galeria.
- [Dashboard unificado pode ficar pesado] → agregações em lote, paginação por cliente/pedido e índices; proibir consultas N+1.
- [Indexação facial privada consumir capacidade] → usar fila durável, métricas por escopo e os mesmos limites operacionais do pipeline vigente.
- [Rollout com frontend/backend de versões diferentes] → manter leitura e limpeza dos dados legados, recusar novas gravações administrativas por IDs existentes com erro explícito e publicar o frontend que usa privada vazia, seleção automática da cliente e uploads próprios.

## Migration Plan

1. Adicionar colunas/constraints de escopo privado, tabelas de correção e reabertura e índices de projeção sem alterar registros existentes.
2. Publicar backend compatível que leia e permita limpar acervos legados, aceite uploads privados e recuse endpoints antigos quando tentarem criar novos vínculos administrativos a fotos existentes.
3. Executar backfill apenas dos campos de escopo público dos registros atuais; não mover arquivos nem recriar referências.
4. Publicar o frontend com upload privado, métricas comuns, congelamento/reabertura e área financeira unificada; manter redirecionamentos de rotas antigas.
5. Validar migration em PostgreSQL descartável, isolamento de mídia, regressão facial, fluxo comercial e concorrência/idempotência.
6. Antes de homologação, inventariar SHA, migration, serviços, portas, volumes e estado facial; obter autorização específica de deploy e aplicar backup exclusivo da Markina.
7. Em rollback, restaurar a versão anterior mantendo as estruturas aditivas; uploads privados novos ficam inacessíveis pela interface antiga, mas não são apagados. Não executar downgrade estrutural se houver mídia privada, correções ou reaberturas persistidas.
