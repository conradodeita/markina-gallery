## MODIFIED Requirements

### Requirement: Persistência do histórico privado

O sistema SHALL manter uma biblioteca visual para a cliente autorizada, onde ela retoma apenas galerias derivadas, pastas liberadas, seleções, pedidos e histórico sem acesso ao acervo-mãe. A interface SHALL identificar fotos já compradas e preservar acesso a histórico permitido após a expiração da seleção. A seleção persistida no servidor SHALL ser retomável no carrinho consolidado após navegação, fechamento do navegador ou nova autenticação da mesma identidade. As compras SHALL apresentar pagamentos agrupados como uma compra com suas galerias e pedidos, sem duplicar os pedidos integrantes como compras independentes; pedidos legados sem agrupamento SHALL permanecer visíveis.

#### Scenario: Biblioteca vazia
- **WHEN** a cliente autenticada não possui galeria derivada ativa nem entrega histórica
- **THEN** a interface mostra estado vazio claro sem sugerir ou revelar galerias de terceiros

#### Scenario: Nova pasta liberada
- **WHEN** o fotógrafo libera uma nova pasta autorizada para a cliente
- **THEN** a biblioteca ou galeria apresenta a nova rodada separadamente das fotos já revisadas

#### Scenario: Histórico após expiração
- **WHEN** o prazo de seleção de uma galeria privada expira
- **THEN** a cliente continua acessando seus pedidos, entregas e identificação de fotos já compradas, sem poder criar seleção fora das regras de reativação

#### Scenario: Retomada em nova sessão
- **WHEN** a mesma cliente autentica novamente, inclusive em outro dispositivo
- **THEN** o servidor restaura suas seleções persistidas e compras autorizadas com a elegibilidade atual
- **AND** uma alteração ainda não salva é identificada como pendente ou falha, nunca apresentada como persistida

#### Scenario: Troca de identidade no dispositivo
- **WHEN** outra cliente autentica no mesmo navegador
- **THEN** contagens, fotos, carrinho, PIX e compras pertencem somente à identidade autenticada atual

#### Scenario: Histórico agrupado e legado
- **WHEN** a cliente possui uma compra com duas galerias e um pedido legado separado
- **THEN** o histórico mostra duas compras, permitindo consultar fotos, valores, status e entregas dos respectivos pedidos

## ADDED Requirements

### Requirement: Destinos independentes para seleção e histórico

O sistema SHALL disponibilizar `Galerias`, `Carrinho` e `Compras` durante a navegação autenticada. Consultar ou falhar ao carregar um destino SHALL NOT apagar a seleção nem impedir o acesso aos outros. O histórico SHALL conter compras cujo pagamento foi comunicado ou confirmado e seus estados posteriores, sem apresentar revisões editáveis como compras concluídas.

#### Scenario: Histórico indisponível
- **WHEN** a consulta de compras falha ou demora
- **THEN** a cliente pode acessar galerias e carrinho, enquanto compras oferece estado próprio de carregamento ou nova tentativa

#### Scenario: Retorno à escolha de fotos
- **WHEN** a cliente sai da revisão para uma galeria e depois volta ao carrinho
- **THEN** encontra suas seleções persistidas e a revisão de todas as galerias autorizadas, sem reiniciar o pedido
