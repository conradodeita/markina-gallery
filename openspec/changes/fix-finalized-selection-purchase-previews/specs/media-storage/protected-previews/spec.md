# Spec Delta

## MODIFIED Requirements

### Requirement: Entrega privada por papel

O sistema SHALL entregar prévias somente após autenticação e autorização da galeria e da pasta para a cliente, por compra confirmada ou seleção sem cobrança finalizada da própria cliente, ou pelo papel administrativo. O portal SHALL apresentar as prévias autorizadas dos itens em Compras. Nenhuma URL persistente de prévia SHALL conceder acesso por posse ou ignorar essas condições.

#### Scenario: Prévia do cliente

- **WHEN** a cliente autorizada abre uma foto de pasta comum ou atribuída a ela
- **THEN** o sistema entrega somente a prévia protegida daquela foto, sem revelar foto, galeria ou original de terceiros

#### Scenario: Prévia administrativa

- **WHEN** o fotógrafo autenticado abre uma foto para conferência
- **THEN** o sistema entrega prévia administrativa sem marca-d'água, limitada à resolução de conferência, sem download do original

#### Scenario: Acesso indevido

- **WHEN** uma sessão sem atribuição solicita uma prévia de pasta restrita por identificador ou caminho
- **THEN** o sistema nega a solicitação sem revelar a existência da foto, mesmo quando a sessão pode ver outras pastas da mesma galeria

#### Scenario: Prévia de compra confirmada após revogação da pasta

- **WHEN** uma cliente acessa o item do próprio pedido canônico confirmado após perder a atribuição à pasta
- **THEN** o sistema entrega a prévia protegida desse item, mas nega a prévia operacional da pasta e nega o item a outra cliente ou a pedido não confirmado

#### Scenario: Prévia da seleção sem cobrança finalizada em Compras

- **WHEN** a cliente abre as fotos do próprio pedido canônico sem cobrança já finalizado, com prévia disponível
- **THEN** o portal exibe a prévia protegida fornecida pela rota autenticada do item, preservando o estado Seleção finalizada e sem exigir confirmação de pagamento

#### Scenario: Compatibilidade das rotas de prévia autorizadas

- **WHEN** a API fornece uma rota interna de prévia de item de compra, de mídia histórica ou de foto autorizada da galeria
- **THEN** o portal solicita essa prévia com um único prefixo de API e a autenticação vigente, sem substituir a rota comercial pela rota operacional

#### Scenario: URL indevida ou falha de entrega

- **WHEN** o caminho não corresponde às rotas internas permitidas de prévia, ou a imagem autorizada falha ao carregar
- **THEN** o portal mantém o fallback de indisponibilidade e os dados do pedido, sem solicitar URL externa, rota administrativa ou original como alternativa
