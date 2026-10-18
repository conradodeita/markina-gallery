## ADDED Requirements

### Requirement: Pendências prioritárias como filtro inicial
O painel SHALL iniciar e limpar filtros para `reported` e `confirmed_undelivered`, sem criar estado persistido. SHALL oferecer Todos e cada estado financeiro individual. Cliente, galeria, período, ordem e cursor SHALL continuar combináveis. Todos SHALL incluir seleções abertas nas condições existentes.

#### Scenario: Iniciar e limpar
- **WHEN** o fotógrafo abre o painel ou limpa os critérios
- **THEN** somente pedidos comunicados ou confirmados sem entrega são listados e a paginação reinicia

#### Scenario: Todos e estado individual
- **WHEN** o fotógrafo seleciona Todos ou uma situação individual
- **THEN** a consulta aplica exatamente esse escopo com os demais critérios

### Requirement: Seleção de cliente aplica imediatamente
Selecionar uma sugestão por mouse ou Enter SHALL aplicar o cliente exato imediatamente, mantendo filtros já aplicados, debounce, cancelamento de sugestões e acessibilidade. A busca livre SHALL manter Aplicar. Resultados obsoletos SHALL NOT substituir a consulta atual.

#### Scenario: Escolher sugestão
- **WHEN** uma sugestão é selecionada por mouse ou teclado
- **THEN** uma consulta com cliente exato e filtros aplicados é iniciada sem exigir Aplicar

### Requirement: Pedidos organizados preservam operação
A interface SHALL reutilizar tokens e UI Kit, agrupando clientes e pedidos expansíveis com identificador, galeria, quantidade, total e status. O detalhe SHALL organizar fotografias, pagamento e entrega preservando campos, capacidades, decisões PIX agrupadas, reaberturas, mensagens, histórico e indicadores existentes.

#### Scenario: Conferir pedido
- **WHEN** o fotógrafo expande um pedido
- **THEN** encontra seus itens, dados financeiros e controles de entrega condicionados às mesmas capacidades do servidor

### Requirement: Prévias administrativas sob demanda
Detalhes SHALL carregar miniaturas existentes somente quando abertos, com tamanho visual de 56–72 px, proporção preservada e fallback. A ampliação SHALL abrir modal sobre toda a interface, com fechar, Escape, clique externo, setas, foco contido/restaurado e scroll bloqueado. Somente a prévia ativa SHALL carregar ampliada; originais e acesso fora do pedido autorizado SHALL NOT ser servidos.

#### Scenario: Ampliação preserva contexto
- **WHEN** o fotógrafo abre, navega e fecha uma prévia do pedido
- **THEN** filtros, cartões, paginação e posição da página permanecem disponíveis e o foco retorna ao acionador

### Requirement: CSV financeiro filtrado completo
Exportar CSV SHALL consultar todos os pedidos autorizados dos filtros aplicados, sem limitar ao cursor visível, com uma linha por pedido e clientes contíguos. As colunas SHALL ser exatamente Nome do cliente, Item/descrição, Total dos itens/pedido, Data e hora. Descrição SHALL usar quantidade e galeria; total SHALL usar pedido; data SHALL ser confirmação efetiva ou vazio.

#### Scenario: Exportar além da paginação
- **WHEN** o fotógrafo exporta uma consulta com mais clientes que a página carregada
- **THEN** recebe todos os pedidos filtrados, separados por pedido e agrupados por cliente

### Requirement: CSV seguro e compatível
CSV SHALL usar UTF-8 com BOM, ponto e vírgula, moeda decimal brasileira e confirmação em America/Sao_Paulo. Texto não confiável SHALL ser protegido contra fórmulas e escapado. Exportação SHALL exigir admin, tratar vazio/erro/carregamento e preservar escopo da conta atual sem expor imagens, telefone, IDs ou colunas adicionais.

#### Scenario: Texto e pedido sem confirmação
- **WHEN** nome/galeria contém fórmula, aspas ou separador e pagamento não está confirmado
- **THEN** o CSV mantém quatro campos seguros e deixa a data vazia
