## ADDED Requirements

### Requirement: Conferência única das fotos no carrinho

Ao abrir o carrinho, o portal da cliente SHALL apresentar as fotos selecionadas uma única vez na grade principal da conferência. O resumo flutuante SHALL manter quantidade, total, cálculo comercial e próxima ação, mas SHALL NOT abrir nem renderizar uma segunda lista, gaveta ou painel de miniaturas sobre a grade. O diálogo de proteção de direitos autorais SHALL permanecer independente e inalterado.

#### Scenario: Cliente prossegue com fotos selecionadas

- **WHEN** a cliente seleciona uma ou mais fotos e abre o carrinho
- **THEN** as fotos selecionadas aparecem na grade principal da conferência
- **AND** nenhuma lista duplicada de miniaturas encobre a galeria no resumo flutuante

#### Scenario: Resumo comercial permanece disponível

- **WHEN** o carrinho possui itens e cotação válida
- **THEN** a cliente continua vendo quantidade, total, cálculo por faixas aplicável e ação para avançar ao PIX

#### Scenario: Proteção autoral permanece independente

- **WHEN** o aviso de proteção autoral deve ser apresentado no carrinho
- **THEN** o diálogo continua disponível sem depender do painel duplicado removido
