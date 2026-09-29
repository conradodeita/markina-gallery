# Spec Delta

## ADDED Requirements

### Requirement: Prévia protegida de foto selecionada no carrinho canônico

O carrinho da cliente autenticada SHALL apresentar a prévia protegida disponível de cada foto selecionada na galeria canônica pela rota operacional autorizada. O frontend SHALL aceitar somente rotas locais de prévia protegida previstas para galeria canônica, galeria legada e histórico da própria cliente; SHALL NOT buscar originais, rotas administrativas, URLs externas ou caminhos manipulados como alternativa. O backend SHALL manter a autorização por cliente, galeria e pasta em cada requisição de mídia.

#### Scenario: Cliente revisa compra com cobrança

- **WHEN** uma cliente autorizada abre o carrinho com foto selecionada cuja prévia está disponível na galeria canônica
- **THEN** a miniatura no carrinho carrega a mesma prévia protegida, sem exigir pagamento ou mudar o estado do pedido

#### Scenario: Foto de pasta restrita de outra cliente

- **WHEN** uma sessão sem atribuição tenta acessar diretamente a rota de prévia mostrada em outro carrinho
- **THEN** o backend nega a mídia sem revelar a foto nem recorrer a um arquivo original

#### Scenario: URL de mídia indevida ou prévia ausente

- **WHEN** o carrinho recebe URL externa, rota administrativa, caminho manipulado ou prévia inexistente
- **THEN** a interface mostra um estado curto de indisponibilidade e não tenta carregar uma alternativa insegura
