## ADDED Requirements

### Requirement: Biblioteca progressiva e responsiva

O sistema SHALL apresentar a primeira jornada autorizada da cliente sem aguardar a conclusão de consultas de histórico comercial que não sejam necessárias para essa primeira renderização. A navegação para a biblioteca SHALL fornecer feedback imediato, e falha ou lentidão no histórico SHALL NOT ocultar jornadas já carregadas nem transformar dados incompletos em estado vazio definitivo.

#### Scenario: Jornada disponível antes do histórico

- **WHEN** os dados essenciais da biblioteca chegam antes do histórico de pedidos
- **THEN** a cliente vê suas jornadas e ações autorizadas enquanto o histórico mantém um estado de carregamento próprio

#### Scenario: Histórico comercial demora ou falha

- **WHEN** a consulta do histórico comercial demora ou falha depois que as jornadas foram carregadas
- **THEN** a biblioteca mantém as jornadas utilizáveis e apresenta no histórico um estado localizado de carregamento, erro ou nova tentativa

#### Scenario: Entrada na biblioteca

- **WHEN** a cliente aciona `Sua biblioteca` ou `Minha biblioteca`
- **THEN** a rota fornece feedback visual imediato até a primeira seção útil ser apresentada

#### Scenario: Crescimento de galerias e pedidos

- **WHEN** a cliente possui várias galerias e pedidos autorizados
- **THEN** a obtenção da biblioteca preserva projeções em lote e não cresce uma consulta adicional por galeria ou pedido

### Requirement: Conferência visual separada por pedido

O sistema SHALL manter pedidos de galerias diferentes e pedidos complementares da mesma galeria como registros comerciais separados. Ao acionar `Ver fotos`, a cliente SHALL visualizar simultaneamente todas as fotos daquele pedido em grade responsiva, com quatro colunas em desktop e duas colunas em mobile, preservando ampliação individual e sem depender de navegação `Anterior`/`Próxima` para conhecer o conjunto.

#### Scenario: Pedido aguardando pagamento

- **WHEN** a cliente abre as fotos de um pedido aguardando pagamento
- **THEN** somente as fotos daquele pedido aparecem juntas em grade, sem serem combinadas com outro pedido ou galeria

#### Scenario: Pedido com pagamento informado

- **WHEN** a cliente abre as fotos de um pedido cujo pagamento foi informado
- **THEN** as fotos congeladas desse pedido aparecem juntas e mantêm o estado comercial correspondente

#### Scenario: Grade em desktop

- **WHEN** a cliente visualiza as fotos de um pedido em navegador desktop
- **THEN** a grade usa quatro colunas e aproveita a largura útil da tela sem distorcer as imagens

#### Scenario: Grade em mobile

- **WHEN** a cliente visualiza as fotos de um pedido em viewport mobile
- **THEN** a grade usa duas colunas com controles legíveis, sem overflow horizontal e com ampliação individual disponível

### Requirement: Ações da biblioteca identificáveis

Todas as ações interativas da biblioteca SHALL exibir rótulo visível, contraste suficiente e nome acessível coerente com seu destino ou efeito. Regras visuais herdadas SHALL NOT ocultar o texto de links ou botões.

#### Scenario: Ação principal de uma jornada

- **WHEN** a biblioteca apresenta a próxima ação de uma jornada
- **THEN** a cliente lê o rótulo completo do link ou botão e consegue identificá-lo por teclado e leitor de tela
