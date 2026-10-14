## ADDED Requirements

### Requirement: Retomada comercial por jornada autorizada

O sistema SHALL devolver, para cada jornada autorizada da cliente, o carrinho vigente, pedidos congelados e ações permitidas daquela Galeria pública sem expor a galeria privada operacional como evento concorrente. Esse estado SHALL ser persistido no servidor e retomável após nova autenticação ou em outro dispositivo.

#### Scenario: Retorno em outro dispositivo

- **WHEN** a cliente autentica novamente e abre uma galeria na qual deixou um carrinho ou pedido
- **THEN** o backend restaura somente o estado comercial daquela cliente e oferece a ação adequada para continuar ou consultar

#### Scenario: Várias galerias na biblioteca

- **WHEN** a cliente possui carrinhos ou pedidos em mais de uma Galeria pública
- **THEN** a biblioteca apresenta cada jornada separadamente com sua própria quantidade, estado e ação, sem somar os carrinhos

#### Scenario: Galeria expirada

- **WHEN** o prazo de uma galeria termina
- **THEN** a cliente continua consultando carrinho e pedidos existentes, não pode modificar nem finalizar o carrinho expirado e pode solicitar reabertura conforme a política vigente

#### Scenario: Isolamento entre clientes

- **WHEN** duas clientes têm acesso ao mesmo acervo privado compartilhado
- **THEN** cada uma recebe somente seu carrinho, seus pedidos e seus estados por foto
