# Spec Delta

## MODIFIED Requirements

### Requirement: Entrega privada por papel

O sistema SHALL entregar prévias somente após autenticação e autorização da galeria e da pasta para a cliente, por compra confirmada da própria cliente ou pelo papel administrativo. Nenhuma URL persistente de prévia SHALL conceder acesso por posse ou ignorar essas condições.

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
