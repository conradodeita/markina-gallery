## ADDED Requirements

### Requirement: Fotos selecionadas aparecem uma vez na revisão consolidada

A revisão global do carrinho SHALL apresentar cada foto selecionada uma única vez, agrupada por galeria e pasta quando aplicável. O resumo comercial SHALL mostrar quantidades, subtotais, total e ações de pagamento sem duplicar miniaturas.

#### Scenario: Cliente abre a revisão global

- **WHEN** a cliente abre o carrinho com fotos selecionadas em uma ou mais galerias
- **THEN** cada foto aparece uma vez no grupo da sua galeria e pasta
- **AND** o resumo comercial não renderiza uma segunda lista de miniaturas

### Requirement: PIX preparado permanece vinculado à revisão editável

Antes da comunicação do pagamento, o PIX preparado SHALL permanecer vinculado à seleção editável no servidor. Uma alteração SHALL invalidar a revisão e o PIX anteriores e exigir atualização antes de nova comunicação. Remover o último item SHALL descartar somente rascunhos não comunicados, sem criar compra histórica.

#### Scenario: Seleção muda após preparar PIX

- **WHEN** a cliente remove uma foto depois de preparar o PIX, mas antes de informar pagamento
- **THEN** a tela atualiza a seleção e não mantém disponível para comunicação o PIX da revisão anterior

#### Scenario: Carrinho preparado fica vazio

- **WHEN** a cliente remove todas as fotos antes de informar pagamento
- **THEN** os rascunhos vazios não aparecem como compra no histórico

### Requirement: Aviso autoral permanece na galeria protegida

O aviso de proteção autoral SHALL permanecer disponível na interação de prévia protegida da galeria, independentemente da remoção de miniaturas duplicadas no carrinho.

#### Scenario: Cliente aciona proteção da prévia

- **WHEN** a cliente aciona o menu de contexto ou o comando de salvar sobre uma prévia protegida na galeria
- **THEN** o diálogo autoral continua acessível sem depender de um painel de miniaturas do carrinho
