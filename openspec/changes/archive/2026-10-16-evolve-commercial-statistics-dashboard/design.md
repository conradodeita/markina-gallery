# Design

## Context

A implementação consolidada em `origin/develop` já isola galerias, pedidos, clientes e itens por `tenant_id`. O Monitor persiste a identidade do proprietário em `platform_owner.admin_user_id`; o e-mail `conradodeita@gmail.com` serve somente para identificação inicial e não é uma regra de acesso. Esta change consultará esse mecanismo e as funções centrais de autorização em modo somente leitura, sem alterar o Monitor.

Os dados comerciais incluem `SaleOrder`, `SaleOrderItem`, `PaymentGroup` para PIX e `ProviderPayment` para cartão InfinitePay. Itens preservam preço, arquivo e pasta em snapshots. O pedido preserva nome/telefone e nomes/IDs das galerias. Correções de pagamento podem retirar pedidos do estado confirmado ou colocar a transação de cartão em `hold`. Não há reembolso executado pela integração atual.

## Goals / Non-Goals

**Goals:**

- Derivar indicadores, tabelas e exports da mesma consulta com tenant e filtros idênticos.
- Exibir valores em centavos e conciliar itens com total de cada pedido, preservando divergências.
- Gerar arquivo HTML independente e CSV de linhas por item, sem estado de sessão, URL de mídia ou credenciais.
- Permitir CSV somente à conta de proprietário validada pelo UUID e manter o escopo de dados no tenant da sessão dessa conta.
- Expor limitações quando a origem não registra a informação requerida.

**Non-Goals:**

- Alterar o Monitor, sua autorização, suas tabelas, grants, UI, endpoints ou migrations.
- Implementar reembolsos, novos meios de pagamento ou nova infraestrutura.
- Classificar toda seleção não paga como abandono.
- Persistir relatórios exportados no servidor.

## Decisions

1. **Autorização do CSV.** O endpoint chama a autenticação administrativa e a resolução/revalidação de tenant existentes; além disso, chama `require_owner` do Monitor antes de consultar vendas e revalida a propriedade após a consulta. Não compara e-mail no endpoint nem aceita tenant do browser. A resposta fica limitada ao tenant da sessão do proprietário. Qualquer falha ou ausência do registro do proprietário nega o acesso.
2. **Fonte canônica.** Pedidos e itens entram na consulta quando o status financeiro atual permanece confirmado. Pagamentos InfinitePay em estado diferente de `confirmed` são excluídos/sinalizados; PIX usa o estado atual do grupo e a confirmação dos pedidos. Estados pendentes, recusados, cancelados ou corrigidos não são receita. A consulta e as exportações usam a mesma data comercial (`confirmed_at`) e os mesmos filtros.
3. **Unidade de venda.** Cada `SaleOrderItem` representa uma fotografia vendida. A quantidade de itens é o número de linhas comerciais; a identidade da foto é o snapshot de UUID/arquivo e sua pasta também vem do snapshot para sobreviver à remoção operacional. Valores por pasta são somas dos itens daquela pasta, sem ratear o total do pedido.
4. **Conciliação.** O total dos itens é a soma de `unit_price_cents` (uma unidade por item). A API compara esse valor ao `SaleOrder.total_cents`, retorna pedido/esperado/calculado/diferença e não altera silenciosamente nenhum valor. Sem campos persistidos de frete, desconto ou taxa, o relatório identifica a divergência sem inventar um ajuste. Reembolso não é suportado como evento próprio; não se declara receita líquida de reembolsos.
5. **Pagamento e destino.** PIX e cartão são identificados pelos vínculos persistidos (`PaymentGroup` e `ProviderPayment`). O rótulo de destino segue o mapeamento solicitado: PIX → Nubank; crédito → InfinityPay. Para qualquer forma desconhecida, o campo de destino fica vazio e o relatório informa que não há mapeamento.
6. **Abandono por expiração da galeria.** Decisão do proprietário em 16/10/2026: usar somente o prazo de seleção/expiração já persistido para a galeria/cliente. Uma oportunidade é abandonada quando o prazo venceu, há seleção persistida e não existe pedido de qualquer estado para aquele cliente e galeria. Pedido pendente, cancelado ou finalizado sem cobrança é seu próprio estado; qualquer pedido confirmado impede que a seleção seja reportada como abandono atual. Não é necessário novo evento ou migration. `PhotoSelection` não guarda preço; se não houver preço congelado ligado à seleção, o valor potencial fica nulo/indisponível, nunca calculado com preço atual.
7. **Conversão de seleções resolvidas.** Cada chave única cliente/galeria/fotografia conta uma vez. O denominador inclui fotografias selecionadas com item em pedido financeiramente confirmado e fotografias selecionadas expiradas sem qualquer pedido; os outros estados de pedido e seleções ainda não vencidas ficam fora. Numerador é a parcela comprada. Sem denominador, taxa é indisponível.
8. **Formato e cache.** CSV usa UTF-8, `;`, decimal com ponto, cabeçalhos estáveis e escaping CSV padrão; cada linha é um item e nunca repete total do pedido como valor da linha. HTML inclui dados e estilos necessários para abrir offline. Ambos são respostas em memória, `private, no-store`, `nosniff`, sem tokens ou URLs privadas.

## Risks / Trade-offs

- O relacionamento de pagamento agrupado pode cobrir mais de um pedido; cada pedido deve aparecer uma vez e os itens permanecem atribuídos à galeria/pasta persistida.
- Conta destino é um rótulo solicitado pelo produto, não confirmação bancária de recebedor. A UI e exports devem rotulá-la como destino mapeado, não como reconciliação bancária.
- Seleções sem preço congelado podem ser contadas como abandonadas, mas seu valor potencial permanece indisponível; a taxa de conversão só pode usar oportunidades com escopo e denominador observáveis.
- O modelo não relaciona cada seleção com pasta ou meio/status de pagamento; nesses recortes, a interface marca abandono/conversão e seleção sem compra como indisponíveis, sem exibir zero.
- O CSV é mais privilegiado que a página: a negação precisa ocorrer antes de ler os dados do tenant e deve ser coberta por sessão, proprietário e isolamento.

## Migration Plan

Não se prevê migration para a venda/exportação nem para abandono: a decisão aprovada usa somente `selection_expires_at` já persistido em `GalleryClientState` ou `DerivedGallery`; seleção sem vencimento configurado não será classificada. Nenhum deploy ou alteração de dados externos faz parte desta change.
