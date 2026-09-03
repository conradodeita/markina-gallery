## MODIFIED Requirements

### Requirement: Entrega privada por papel
O sistema SHALL entregar prévias somente após autenticação e autorização decidida pelo backend. Uma referência da galeria privada poderá ser entregue a todos os seus membros ativos, mas seleção, comentário, compra ou pagamento de um membro SHALL NOT conceder nem revelar estado a outro. URL persistente, original e privada irmã SHALL permanecer inacessíveis.

#### Scenario: Prévia de membro ativo
- **WHEN** uma cliente associada e não bloqueada solicita foto disponível na privada
- **THEN** o sistema entrega somente a prévia protegida e seus próprios estados autorizados

#### Scenario: Prévia do cliente
- **WHEN** a cliente autorizada abre uma foto disponível em sua privada
- **THEN** o sistema entrega somente a prévia protegida daquela foto e não revela outra privada, estado de terceiro ou original

#### Scenario: Prévia administrativa
- **WHEN** o fotógrafo autenticado abre foto para conferência
- **THEN** o sistema entrega prévia administrativa limitada sem download do original

#### Scenario: Publicação automática segura
- **WHEN** o worker termina a geração do derivado protegido `client_preview` de uma foto de conteúdo
- **THEN** o sistema marca a foto disponível e libera sua pasta de modo idempotente, sem disponibilizar o arquivo original nem foto cujo derivado ainda não esteja pronto

#### Scenario: Membro bloqueado
- **WHEN** uma cliente bloqueada solicita prévia operacional da privada
- **THEN** o sistema nega sem apagar nem impedir seu histórico comercial autorizado

#### Scenario: Acesso indevido
- **WHEN** sessão sem associação solicita prévia por identificador ou caminho
- **THEN** o sistema nega sem revelar se arquivo, galeria ou membro existem
