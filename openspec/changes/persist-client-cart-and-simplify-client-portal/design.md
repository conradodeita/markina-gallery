## Context

Consulte `proposal.md` e os três delta specs. A implementação atual mantém a seleção em `PhotoSelection`, mas `create_pending_checkout` cria `SaleOrder`/`SaleOrderItem` e apaga essas linhas ao clicar em `Prosseguir`. A tela conserva o detalhe apenas em estado React; numa visita posterior, `/gallery/{id}/payment-communications` devolve o pedido sem itens e a biblioteca consulta apenas compras confirmadas. Por isso a cliente não retoma a conferência completa.

O roadmap e as changes `consolidate-shared-private-galleries-and-progressive-sales` e `complete-private-gallery-operations-and-sales` já estabelecem carrinho por cliente e Galeria pública, pedido complementar, isolamento entre membros, confirmação manual e histórico após expiração. Esta change corrige a fronteira de congelamento e a superfície de retomada sem substituir a projeção comercial, a reabertura ou a administração financeira dessas changes.

## Goals / Non-Goals

**Goals:**

- Usar o servidor como única autoridade do carrinho, do rascunho e dos pedidos.
- Tornar seleção, conferência, comunicação e retorno transições idempotentes e coerentes.
- Preservar pedidos existentes e permitir rollout/rollback sem perda comercial.
- Entregar uma interface curta, móvel e orientada à próxima ação.

**Non-Goals:**

- Alterar preços, PIX, confirmação administrativa, WhatsApp ou regras de expiração/reabertura.
- Criar carrinho entre Galerias públicas, recompra de foto confirmada ou acesso a outra cliente.
- Modificar busca/indexação facial; seus resultados apenas consumirão o mesmo estado comercial.
- Implementar cancelamento pela cliente, estorno, pagamento automático ou novo provedor.

## Decisions

### 1. `PhotoSelection` continua sendo a autoridade do carrinho editável

Enquanto não houver comunicação de pagamento, as linhas de seleção representam o carrinho atual. `Prosseguir` cria ou atualiza um rascunho de `SaleOrder`, mas não apaga a seleção. Itens, cotação e snapshots do rascunho podem ser substituídos porque ainda não constituem o registro financeiro congelado.

Alternativa descartada: manter a ordem atual e reconstruir o carrinho a partir de `SaleOrderItem`. Isso confunde snapshot comercial com intenção editável e dificulta distinguir compra complementar.

### 2. O pedido recebe uma fronteira persistida de congelamento

`SaleOrder` ganhará `frozen_at` anulável. Um pedido novo com `payment_status=pending`, sem comunicação e `frozen_at=NULL` é rascunho editável. `Informar pagamento` bloqueia o contexto cliente+galeria, revalida seleção, disponibilidade, prazo e cotação, sincroniza os itens, grava `frozen_at` em UTC, cria uma única `PaymentCommunication` e remove apenas as seleções incorporadas, tudo na mesma transação.

Uma restrição parcial garante no máximo um rascunho editável por cliente e galeria. As rotas de selecionar, desmarcar, prosseguir e comunicar usarão o mesmo lock de associação/galeria para impedir um conjunto parcialmente congelado.

Alternativa descartada: criar o pedido somente ao comunicar pagamento. Manter um rascunho persistido preserva a URL/detalhe já usado pelo frontend, a idempotência do checkout e a compatibilidade incremental da API.

### 3. Pedidos preexistentes são migrados como congelados

A migration aditiva preenche `frozen_at=created_at` em todos os pedidos existentes antes de tornar a coluna semanticamente ativa. Isso preserva pedidos pendentes cujo checkout antigo já consumiu a seleção e impede que sejam reabertos como carrinhos vazios ou recalculados com preços atuais.

Alternativa descartada: recriar `PhotoSelection` para pedidos pendentes. Essa operação poderia recolocar uma foto em mais de um pedido e alterar uma intenção financeira já apresentada.

### 4. Uma projeção comercial comum alimenta todas as superfícies da cliente

Um serviço compartilhado devolverá, sempre filtrado por `client_id` e Galeria pública/privada autorizada:

- carrinho atual, cotação e itens;
- rascunho retomável, quando existir;
- pedidos congelados com itens e estados de comunicação/confirmado;
- estado de cada foto: `available`, `selected`, `payment_reported` ou `purchased`;
- ações permitidas conforme prazo, vínculo e estado.

Os payloads da biblioteca, Galeria pública, galeria privada e detalhe comercial reutilizarão essa projeção. O frontend não conservará estado comercial em `localStorage`; nova sessão OTP ou outro dispositivo verá o mesmo resultado do backend.

Alternativa descartada: continuar compondo carrinho, pagamento e compras em requisições independentes na página. Isso mantém janelas de inconsistência e repete regras de prioridade de estado.

### 5. A retomada usa uma superfície comercial única por galeria

`Carrinho (n)` aparece na Galeria pública, na privada contextual e no card da biblioteca quando houver seleção. A mesma superfície mostra a revisão editável e, abaixo, pedidos congelados com miniaturas, valor e estado. Depois da comunicação, o pedido deixa o carrinho e permanece em `Pagamento informado`; após confirmação, passa a `Compradas`. Um novo carrinho pode coexistir com pedidos congelados anteriores.

Estados na foto seguem prioridade `purchased` > `payment_reported` > `selected` > `available`. Resultados faciais usam os mesmos IDs e não criam outra seleção.

Alternativa descartada: uma página global que soma galerias. Preço, prazo, PIX e confirmação são autoridades por Galeria pública e não podem ser combinados.

### 6. A redução de texto ocorre nos componentes compartilhados e nos estados reais

A biblioteca usará `Minhas fotos` como título e removerá eyebrow/detalhes que explicam agrupamento ou preservação. Cards mostrarão nome do evento/galeria, um status, quantidade/valor quando útil e uma ação principal. A galeria e a conferência seguirão o mesmo vocabulário: `Carrinho`, `Selecionada`, `Pagamento informado`, `Comprada`, `Ver fotos` e `Ver pedido`.

Mensagens de erro, privacidade, consentimento, expiração e confirmação financeira não serão removidas quando necessárias para decisão ou segurança. Texto acessível invisível pode conservar contexto adicional para leitor de tela.

## Risks / Trade-offs

- [Rascunho e seleção divergirem durante concorrência] → mutex transacional comum, sincronização antes da resposta e revalidação obrigatória ao comunicar.
- [Migration classificar pedido antigo incorretamente como editável] → todo pedido preexistente recebe `frozen_at`, sem reconstrução ou recálculo.
- [Consulta de itens e estados causar N+1 em galerias grandes] → projeções em lote por IDs e testes de volume/contagem de consultas.
- [Cliente interpretar carrinho e pedido congelado como duplicados] → separar visualmente `Carrinho` de `Pedidos`, usar estados curtos e retirar do carrinho somente os itens congelados.
- [Rollback ler pedidos novos sem conhecer `frozen_at`] → schema aditivo permanece; pedidos congelados continuam `pending/confirmed` compatíveis, e nenhuma coluna é removida no rollback.
- [Textos curtos omitirem orientação necessária] → manter ação inequívoca, rótulos acessíveis e mensagens detalhadas somente em erro, expiração, consentimento ou decisão financeira.

## Migration Plan

1. Adicionar `sale_order.frozen_at` e a restrição de rascunho único; preencher pedidos existentes com `created_at` em migration transacional e não destrutiva.
2. Publicar backend compatível que continue lendo os endpoints atuais, passe a manter seleção no checkout e congele no endpoint de comunicação.
3. Estender projeções/payloads de forma aditiva para itens, carrinho, pedidos e estados por foto.
4. Publicar frontend com retomada e textos essenciais; não depender dos novos campos antes de o backend estar saudável.
5. Validar migration PostgreSQL, concorrência, pedidos legados, múltiplas galerias, expiração e isolamento de dois clientes.
6. Em homologação, usar dados sintéticos ou o estado já autorizado, inventariar serviços/volumes e executar deploy somente após autorização específica.
7. Para rollback, reverter somente a aplicação e manter coluna/índice aditivos; não recriar seleções nem descongelar pedidos.
