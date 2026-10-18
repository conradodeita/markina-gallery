# Design

## Context

Consulte `proposal.md` e a delta spec. O checkout agrupado já persiste `PaymentGroup`, associa `SaleOrder` individuais e aplica uma decisão financeira ao escopo do grupo. Eventos de pagamento já usam o ID curto do grupo quando existe, mas passam `sua compra` como valor de `{{galeria}}`; templates que dizem `da galeria {{galeria}}` então produzem “da galeria sua compra”. A tela da cliente usa a referência do grupo e a área administrativa expõe códigos curtos dos pedidos individuais.

A árvore de trabalho contém alterações preexistentes amplas que devem ser preservadas e não misturadas. O produto está em produção; IDs e snapshots são dados históricos imutáveis. Esta change não implementa nem publica código.

## Goals / Non-Goals

**Goals:**

- Permitir localizar no painel uma compra agrupada pelo mesmo prefixo de ID que chegou na notificação e aparece em “Compras”.
- Mostrar os pedidos/galerias que compõem o total, preservar seus códigos e esclarecer o alcance das decisões do grupo.
- Renderizar as mensagens de pagamento com uma frase adequada a grupo ou pedido individual, mantendo o mesmo código existente.
- Preservar mensagens enviadas e snapshots de notificações já persistidos.

**Non-Goals:**

- Gerar, renumerar, converter ou substituir IDs de compras/pedidos.
- Reagrupar pedidos históricos, alterar pagamentos ou reenviar mensagens antigas.
- Alterar regras de preço, contabilização, transações, permissões ou fluxo financeiro definido pela change `unified-client-cart-and-pix`.
- Fazer deploy ou operar dados de produção nesta etapa.

## Decisions

### 1. Compra agrupada é a referência primária; pedidos continuam como detalhes

Quando houver grupo, a interface usará o `PaymentGroup.id` já persistido, truncado pelo mesmo critério existente de oito caracteres, no título da compra. Abaixo, cada item por galeria continuará usando seu `SaleOrder.id` também existente e curto. Os rótulos “Compra” e “Pedido” deixam explícitos os dois níveis.

Alternativa descartada: substituir os IDs individuais pelo ID do grupo. Isso ocultaria a identidade operacional por galeria e quebraria rastreabilidade já usada em produção.

### 2. Reutilizar relações e decisões financeiras atuais

A tela deve consumir a relação já persistida entre `PaymentGroup`, `PaymentCommunication` e `SaleOrder`. Se a projeção existente não trouxer grupo ou composição necessários, ampliar somente a resposta autenticada do painel, sem novo identificador ou mudança no banco. As ações seguem a operação atômica existente para o grupo e mostram todas as galerias e pedidos antes da decisão.

Alternativa descartada: inferir agrupamento no frontend por nome, valor ou horário. Esses dados não são chaves de associação confiáveis.

### 3. Contexto de mensagem é uma frase completa, não um nome de galeria

Adicionar aos templates de pagamento uma variável de contexto que renderiza a frase integral. Para um grupo, ela identifica “o pagamento da compra <código do grupo>”; para um pedido individual, identifica “o pagamento do pedido <código do pedido> da galeria <nome>”. Os templates padrão e a prévia usam essa variável, evitando que uma frase estática “da galeria” seja concatenada ao fallback “sua compra”. Manter as variáveis antigas para compatibilidade nos templates ainda não atualizados.

Para configurações ativas contendo as formas conhecidas `do pedido {{pedido}} da galeria {{galeria}}` em confirmação/recusa e `informou pagamento do pedido {{pedido}}` no aviso ao fotógrafo, disponibilizar uma prévia reversível com transformação idempotente e estreita que substitui somente a frase pela variável de contexto, preservando o restante do texto personalizado. Templates com outras estruturas não serão sobrescritos automaticamente e aparecem como não reconhecidos para revisão manual. A prévia lê também os textos ativos de push sem criar configurações ou alterar versões. Qualquer aplicação remota exige inventário, backup recuperável, revisão do diff e autorização operacional explícita; eventos, snapshots e mensagens já emitidas nunca são alterados.

Alternativa descartada: preencher `{{galeria}}` com “sua compra” em qualquer template. Essa substituição não preserva a gramática do texto ao redor e já causou o defeito observado.

### 4. Compatibilidade histórica e de identificadores

Notificações futuras continuam usando o identificador que o produtor já resolve: ID do grupo quando existe, ID do pedido quando é legado. Não reprocessar snapshots, entregas enfileiradas ou histórico. O painel exibe os IDs existentes sem criar alias persistido.

Alternativa descartada: migration de schema para criar um número comercial sequencial. Ela não é necessária e aumentaria o risco operacional.

## Risks / Trade-offs

- O painel possui atalhos e cards em mais de uma superfície → verificar que todos os caminhos de decisão apresentam o mesmo ID de grupo e não sugerem ação isolada.
- IDs curtos podem colidir entre grupos/pedidos → preservar UUID completo nos destinos e chamadas autenticadas; o código curto serve para localização visual, não como credencial ou chave de autorização.
- Templates personalizados podem usar outra gramática → preservar texto por padrão, mostrar prévia de grupo/individual e migrar somente a frase reconhecida; configurações não reconhecidas exigem revisão.
- Alteração da configuração ativa de mensagem pode impactar notificações futuras → fazer backup/preview, comprovar transformação idempotente e exigir autorização operacional antes de aplicar em produção.
- Atualização visual pode confundir pedidos legados → manter explicitamente o rótulo “Pedido” e o fluxo atual quando `payment_group_id` estiver ausente.

## Migration Plan

Nenhuma migration de schema. Planejar uma transformação reversível e idempotente somente das frases reconhecidas nos templates ativos; preservar todo o restante do texto e todos os snapshots/históricos. Antes de qualquer aplicação em ambiente remoto, inventariar a configuração que será alterada, apresentar diff/preview e plano de impacto zero, obter autorização explícita e fazer backup recuperável. Validar localmente com grupos de duas ou mais galerias, pedido legado, template padrão, o texto reportado e template personalizado não reconhecido. Em produção, confirmar os IDs antes/depois e ausência de alteração em snapshots ou mensagens já emitidas.
