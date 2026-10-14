## Context

Veja `proposal.md` e os três delta specs. A implementação atual apresenta jornadas e pedidos na biblioteca, porém a ação `Ver pedido` abre a galeria privada completa, onde filtros, grade disponível, carrinho e acompanhamento financeiro coexistem. `/library/purchases` também pode devolver pedidos `awaiting_payment`, enquanto a nova decisão de produto define que todo estado anterior à comunicação pertence ao carrinho.

A change `persist-client-cart-and-simplify-client-portal` estabeleceu corretamente a persistência e o isolamento por cliente e Galeria pública, mas descartou uma página global que somasse galerias. A decisão nova substitui apenas essa conclusão de UX: a agregação será uma projeção visual na biblioteca; checkout, PIX, prazo, preço e pedido continuam isolados por galeria.

## Goals / Non-Goals

**Goals:**

- oferecer uma visão global dos carrinhos sem introduzir pedido ou pagamento multigaleria;
- tornar a comunicação de pagamento a fronteira inequívoca entre `Carrinho` e `Compras`;
- reduzir o histórico a informações financeiras essenciais e fotos do próprio pedido;
- reutilizar projeções autoritativas e carregamento progressivo já existentes.

**Non-Goals:**

- alterar cálculo de preço, configuração PIX, prazo, congelamento, confirmação administrativa ou WhatsApp;
- combinar fotos de galerias distintas em um checkout;
- criar migration, copiar seleções ou reclassificar dados persistidos;
- remover filtros das superfícies onde a cliente ainda navega e monta sua seleção.

## Decisions

### 1. A biblioteca será a superfície agregadora

A rota `/library` apresentará seções explícitas `Carrinho`, `Galerias` e `Compras`. `Carrinho` será derivado das jornadas retornadas por `/library`, incluirá somente grupos com seleção retomável e somará quantidade/valor apenas para orientação. Cada card conservará um CTA `Revisar carrinho` para o `review_url` da sua galeria.

Alternativa descartada: criar uma ordem global ou reutilizar uma galeria privada como contêiner de outras galerias. Isso quebraria preço, prazo, PIX e auditoria por Galeria pública.

### 2. A projeção de compras excluirá estados anteriores à comunicação

O endpoint cliente `/library/purchases` devolverá somente pedidos cuja comunicação existe ou cujo pagamento já está confirmado. Estados de rascunho e `awaiting_payment` sem comunicação permanecerão acessíveis pela projeção do carrinho. A filtragem ocorrerá no backend para que diferentes clientes frontend não possam interpretar um rascunho como compra.

Pedidos comunicados preservam sua classificação `payment_reported`; confirmados preservam `purchased`. A change não altera transições nem dados, apenas a projeção autorizada.

Alternativa descartada: receber todos os pedidos e filtrar exclusivamente no React. Isso perpetua contratos ambíguos e pode produzir contagens diferentes entre superfícies.

### 3. A navegação apontará para âncoras sem duplicar páginas

Atalhos globais e cards usarão `/library#cart` e `/library#purchases`. `Ver pedido` será substituído por `Compras` ou `Ver compra`; nunca apontará para a galeria privada completa quando a intenção for consultar histórico. A galeria privada continuará sendo o destino para navegar, selecionar e revisar um carrinho específico.

Alternativa descartada: manter `orders_url` na galeria e esconder partes com um parâmetro de query. Isso mantém duas implementações do histórico e facilita a reintrodução de filtros e fotos redundantes.

### 4. Cards de compra reutilizarão a grade por pedido

`LibraryOrderCard` continuará isolando cada pedido, exibirá cabeçalho essencial e carregará suas miniaturas somente quando expandido. A grade responsiva 4/2 e a ampliação protegida permanecem; controles de favorito, seleção e filtros não serão incluídos no histórico.

Alternativa descartada: apresentar fotos compradas numa grade única. Isso apagaria a separação entre pedidos complementares e galerias diferentes.

### 5. Falhas permanecem localizadas

O carregamento de jornadas/carrinhos e o de compras continuarão independentes. Um erro em `/library/purchases` não ocultará carrinhos; um erro de cotação será mostrado somente no grupo afetado. A soma geral será omitida ou marcada indisponível quando algum subtotal não for autoritativo.

Alternativa descartada: bloquear toda a biblioteca até todas as projeções concluírem. Isso reintroduziria a lentidão já corrigida anteriormente.

## Risks / Trade-offs

- [A soma geral parecer um checkout único] → rotular como resumo e informar junto aos CTAs que cada galeria é finalizada separadamente.
- [Pedido comunicado ainda aparecer por alguns instantes no carrinho] → atualizar as duas projeções após a resposta bem-sucedida de comunicação e confiar no backend na próxima carga.
- [Pedido legado `awaiting_payment` desaparecer do histórico] → mantê-lo retomável no carrinho conforme sua seleção/rascunho; cobrir compatibilidade em teste direcionado.
- [Âncoras abrirem antes da consulta progressiva terminar] → reservar as seções com estado próprio e aplicar foco/rolagem quando o conteúdo chegar.
- [Mudança de endpoint afetar consumidor administrativo] → confirmar consumidores; a filtragem será exclusiva do endpoint autenticado da cliente.

## Migration Plan

1. Criar testes inicialmente falhos para a fronteira de projeção, carrinhos de várias galerias, total informativo, navegação e ausência de filtros.
2. Ajustar a projeção cliente de compras sem migration e verificar isolamento, pedidos complementares e compatibilidade.
3. Reorganizar a biblioteca em `Carrinho`, `Galerias` e `Compras`, mantendo carregamentos independentes e componentes responsivos existentes.
4. Atualizar rótulos e destinos oficiais e remover o uso cliente de `Ver pedido` para abrir a galeria completa.
5. Executar testes direcionados, lint, typecheck, build e OpenSpec estrito; ampliar validação somente diante de falha compartilhada.
6. Publicar em homologação pelo fluxo autorizado, sem backfill ou mutação comercial, e validar desktop/mobile autenticados.

Rollback restaura frontend e filtro da projeção anterior sem alterar fotos, seleções, pedidos, pagamentos ou comunicações persistidas.
