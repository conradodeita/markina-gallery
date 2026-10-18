# gallery-sales/payment-operations-dashboard Specification

## Purpose

Permitir ao fotógrafo revisar pagamentos e entregas por cliente, priorizando visualmente as situações financeiras e tornando a lista mais rápida de percorrer.

## Requirements

### Requirement: Situação financeira composta por entrega
O sistema SHALL distinguir, em cada pedido, `Pagamento confirmado` de `Pagamento confirmado - fotos não entregue`. Um pedido SHALL receber a segunda situação quando o pagamento estiver confirmado e não houver nenhum link de fotos prontas salvo no campo `Link externo do álbum`. Um pedido confirmado com link nesse campo SHALL permanecer como `Pagamento confirmado`. A classificação SHALL NOT alterar pagamento, link, notificação ou acesso da cliente.

#### Scenario: Pedido confirmado sem álbum
- **WHEN** o fotógrafo consulta um pedido cujo pagamento foi confirmado e o campo `Link externo do álbum` não possui nenhum link de fotos prontas salvo
- **THEN** o painel classifica o pedido como `Pagamento confirmado - fotos não entregue`

#### Scenario: Pedido confirmado com álbum
- **WHEN** o fotógrafo consulta um pedido cujo pagamento está confirmado e possui link de fotos prontas salvo no campo `Link externo do álbum`
- **THEN** o painel classifica o pedido como `Pagamento confirmado`

#### Scenario: Link salvo em pedido não confirmado
- **WHEN** um pedido possui link salvo, mas seu estado financeiro não está confirmado
- **THEN** o painel preserva a situação financeira existente e não o classifica como confirmação paga

### Requirement: Prioridade dos grupos de clientes
Com `Situação financeira` em `Todas`, o painel SHALL agrupar os cards na ordem `Pagamento comunicado`, `Pagamento confirmado`, `Pagamento confirmado - fotos não entregue`, `Aguardando pagamento`, `Pagamento não localizado`, `Prazo expirado` e demais estados. Dentro de cada grupo, SHALL ordenar clientes da chegada mais antiga para a mais recente, com desempate estável.

#### Scenario: Lista sem filtro financeiro
- **WHEN** o fotógrafo abre Vendas e pagamentos com situação financeira `Todas`
- **THEN** os cards aparecem agrupados na ordem de prioridade especificada e, dentro de cada grupo, da chegada mais antiga para a mais recente

#### Scenario: Chegada igual
- **WHEN** dois clientes do mesmo grupo têm a mesma data de chegada
- **THEN** o painel usa um desempate estável para manter a ordem entre consultas

#### Scenario: Seleção sem pedido
- **WHEN** a cliente tem fotos selecionadas, mas ainda não preparou o checkout e não existe pedido
- **THEN** seu card `No carrinho` permanece em grupo separado depois dos grupos financeiros e não é classificado como `Aguardando pagamento`

### Requirement: Situação prioritária do card de cliente
Para cliente com pedidos em mais de uma situação, o card SHALL usar a situação de maior prioridade presente entre seus pedidos no resultado. Os pedidos SHALL continuar visíveis com seus estados e ações individuais.

#### Scenario: Cliente com pedidos em várias situações
- **WHEN** uma cliente tem mais de um pedido visível em situações diferentes
- **THEN** o card aparece uma única vez na posição determinada pela situação de maior prioridade e mantém cada pedido e estado individual

#### Scenario: Situação financeira filtrada
- **WHEN** o fotógrafo seleciona uma situação específica
- **THEN** o painel retorna clientes que possuem pedidos nessa situação e conserva a ordem de chegada dentro do resultado

#### Scenario: Paginação de clientes
- **WHEN** existem mais clientes do que cabem em uma página
- **THEN** páginas sucessivas preservam a mesma prioridade e ordem de chegada sem duplicar nem omitir clientes

### Requirement: Cores coerentes com as situações financeiras
O sistema SHALL usar amarelo para `Pagamento comunicado`, verde para `Pagamento confirmado`, vermelho para `Pagamento confirmado - fotos não entregue`, azul para `Aguardando pagamento`, cinza para `Pagamento não localizado` e roxo para `Prazo expirado`. O card SHALL usar a cor da situação primária do cliente e cada opção do filtro SHALL usar a cor da própria situação. Texto e contraste SHALL identificar o estado independentemente da cor e permanecer legíveis nos temas suportados.

#### Scenario: Card e opção no filtro
- **WHEN** a situação financeira está representada no card e no filtro
- **THEN** ambos usam a mesma cor e apresentam o rótulo textual completo

#### Scenario: Acessibilidade da situação
- **WHEN** a pessoa usa tema escuro, teclado ou tecnologia assistiva
- **THEN** texto, foco e nome acessível identificam a situação sem depender da cor

### Requirement: Filtro de entrega de mensagem aposentado
Vendas e pagamentos SHALL NOT apresentar o filtro `Entrega de mensagem` nem enviar seu parâmetro nas consultas iniciadas pela interface. A remoção do filtro SHALL NOT remover estados de mensagens usados em outros elementos do painel, telemetria, notificações ou contratos com outros consumidores.

#### Scenario: Filtros disponíveis
- **WHEN** o fotógrafo abre os filtros de Vendas e pagamentos
- **THEN** o filtro financeiro está disponível com todas as situações e o filtro de entrega de mensagem não aparece

#### Scenario: Aplicação dos filtros restantes
- **WHEN** o fotógrafo filtra por cliente, galeria, situação financeira ou período
- **THEN** esses critérios continuam combináveis e são aplicados sem parâmetro de entrega de mensagem

### Requirement: Separação entre carrinho e pedido aguardando pagamento
O sistema SHALL classificar uma seleção sem pedido como `No carrinho`. No fluxo de checkout unificado, preparar o PIX SHALL criar pedidos em rascunho; enquanto houver pedido pendente válido sem comunicação de pagamento, sua situação SHALL ser `Aguardando pagamento`. Registrar `Informar pagamento` SHALL criar a comunicação e a situação SHALL passar a `Pagamento comunicado`.

#### Scenario: PIX preparado
- **WHEN** a cliente abre o carrinho unificado com seleção válida e o checkout prepara o PIX, sem comunicação de pagamento
- **THEN** o pedido aparece como `Aguardando pagamento`

#### Scenario: Pagamento informado
- **WHEN** a cliente aciona `Informar pagamento` para um pedido pendente
- **THEN** a comunicação pendente de revisão aparece como `Pagamento comunicado`

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
