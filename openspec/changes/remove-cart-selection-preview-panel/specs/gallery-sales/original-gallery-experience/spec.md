## ADDED Requirements

### Requirement: Conferência única das fotos no carrinho

Ao abrir o carrinho, o portal da cliente SHALL apresentar as fotos selecionadas uma única vez na grade principal da conferência. O resumo flutuante SHALL manter quantidade, total, cálculo comercial e próxima ação, mas SHALL NOT abrir nem renderizar uma segunda lista, gaveta ou painel de miniaturas sobre a grade. Depois que o pedido PIX for criado, a aplicação SHALL esconder a grade anterior, os filtros, o atalho e o resumo flutuante e SHALL apresentar `Conferência do pedido` como única superfície da etapa final. Essa conferência SHALL permitir ampliar, favoritar e desmarcar as fotos antes da comunicação do pagamento e SHALL manter quantidade, total e recursos PIX logo abaixo. O diálogo de proteção de direitos autorais SHALL permanecer independente e inalterado.

#### Scenario: Cliente prossegue com fotos selecionadas

- **WHEN** a cliente seleciona uma ou mais fotos e abre o carrinho
- **THEN** as fotos selecionadas aparecem na grade principal da conferência
- **AND** nenhuma lista duplicada de miniaturas encobre a galeria no resumo flutuante

#### Scenario: Resumo comercial permanece disponível

- **WHEN** o carrinho possui itens e cotação válida
- **THEN** a cliente continua vendo quantidade, total, cálculo por faixas aplicável e ação para avançar ao PIX

#### Scenario: Pedido PIX substitui a revisão anterior

- **WHEN** a cliente avança e o pedido PIX pendente é criado
- **THEN** a grade da galeria, os filtros, o atalho e o resumo flutuante do carrinho deixam de ser exibidos
- **AND** `Conferência do pedido` mostra uma única lista interativa das fotos seguida por quantidade, total, QR Code, PIX copia e cola e ação de informar pagamento

#### Scenario: Cliente altera a seleção na conferência final

- **WHEN** a cliente amplia, favorita ou desmarca uma foto em `Conferência do pedido`
- **THEN** a interação usa a mesma prévia protegida e persiste a alteração permitida
- **AND** ao desmarcar uma foto, a conferência e o PIX obsoletos deixam de ser apresentados até que um novo pedido seja preparado

#### Scenario: Proteção autoral permanece independente

- **WHEN** o aviso de proteção autoral deve ser apresentado no carrinho
- **THEN** o diálogo continua disponível sem depender do painel duplicado removido
