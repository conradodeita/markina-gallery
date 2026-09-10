## 1. Inventário e contratos de regressão

- [ ] 1.1 Reconciliar implementação e autoridade com `consolidate-shared-private-galleries-and-progressive-sales`, `complete-private-gallery-operations-and-sales`, checkout PIX, projeção comercial, expiração e biblioteca; registrar qualquer desvio no design e verificar por busca reproduzível que a change não altera facial, mídia, preços ou confirmação administrativa.
- [ ] 1.2 Adicionar testes backend inicialmente falhos para carrinho preservado após `Prosseguir`, edição do mesmo rascunho, congelamento somente em `Informar pagamento`, pedido complementar, idempotência/concorrência, isolamento cliente+galeria e pedido legado; verificar que as falhas correspondem ao comportamento atual.
- [ ] 1.3 Adicionar testes frontend inicialmente falhos para `Carrinho (n)`, retomada com miniaturas/valor/estado, marcadores por foto e ausência dos textos excessivos aprovados; cobrir Galeria pública, privada, biblioteca e resultado facial compartilhado.

## 2. Persistência e transação comercial

- [ ] 2.1 Criar migration aditiva para `SaleOrder.frozen_at`, backfill de todos os pedidos existentes como congelados e garantia de um único rascunho editável por cliente+galeria; verificar ciclo `head anterior -> novo head -> downgrade -> novo head` em PostgreSQL e compatibilidade SQLite dos testes.
- [ ] 2.2 Refatorar o checkout para criar ou sincronizar o mesmo rascunho sem apagar `PhotoSelection`, recalculando itens e cotação após adição/remoção; verificar retorno, edição, múltiplas pastas e separação entre Galerias públicas.
- [ ] 2.3 Tornar `Informar pagamento` a transação de congelamento: adquirir lock comum, revalidar prazo/disponibilidade/preço, sincronizar snapshot, gravar `frozen_at`, criar uma comunicação e consumir somente a seleção congelada; verificar clique repetido e corrida com mutação do carrinho.
- [ ] 2.4 Preservar pedidos preexistentes e pedidos já comunicados/confirmados como imutáveis, permitindo novo carrinho complementar sem recompra de foto confirmada; verificar estados pendente legado, não localizado, confirmado e galeria expirada.

## 3. Projeção e APIs da cliente

- [ ] 3.1 Implementar projeção comercial compartilhada e em lote para carrinho, rascunho, pedidos congelados, itens e prioridade `purchased > payment_reported > selected > available`; verificar ausência de N+1 relevante e isolamento entre dois membros do mesmo acervo.
- [ ] 3.2 Estender de forma compatível os payloads da biblioteca, Galeria pública, privada, detalhe do pedido e pagamento para restaurar fotos, totais, estados e ações autorizadas; verificar sessão renovada, outro dispositivo, múltiplas galerias e origem indisponível.
- [ ] 3.3 Aplicar expiração e reabertura às novas mutações: manter consulta de carrinho/pedidos, bloquear edição/comunicação fora do prazo e retomar após aprovação; verificar respostas backend e ausência de autorização inferida pelo frontend.

## 4. Interface curta e retomável

- [ ] 4.1 Criar ou consolidar componente compartilhado de `Carrinho (n)` e revisão por galeria, com miniaturas, total, remoção antes da comunicação, estados de pedidos e CTA único; verificar acessibilidade, mobile/desktop e restauração após reload.
- [ ] 4.2 Integrar os estados comerciais e o carrinho à Galeria pública, privada e resultados faciais, impedindo duplicação/recompra e permitindo novo carrinho complementar; verificar os fluxos manuais e faciais com a mesma foto.
- [ ] 4.3 Simplificar biblioteca e cards para `Minhas fotos`, estado essencial e próxima ação, removendo `Sua área privada`, `Cada evento aparece uma única vez`, `compras preservadas` e explicações redundantes; verificar estados vazio, ativo, pagamento informado, comprado, expirado e origem indisponível.

## 5. Validação, documentação e entrega

- [ ] 5.1 Executar Ruff, testes backend direcionados e completos, migration PostgreSQL, lint/typecheck/testes/build frontend, OpenSpec estrito, gitleaks e `git diff --check`; investigar falhas relacionadas e registrar evidências verificáveis antes de marcar a task.
- [ ] 5.2 Documentar estados, compatibilidade de pedidos legados, concorrência, rollback e roteiro humano de retomada em celular/desktop; verificar que outro executor consegue reproduzir seleção, saída, retorno, edição, comunicação e pedido complementar apenas pelo repositório.
- [ ] 5.3 Preparar inventário zero-impact de homologação com SHA, migration, serviços, portas, volumes, backup, estado facial e rollback; solicitar autorização específica antes de deploy e, somente após autorizada, publicar e confirmar healthchecks sem alterar dados, mídia ou infraestrutura de terceiros.
