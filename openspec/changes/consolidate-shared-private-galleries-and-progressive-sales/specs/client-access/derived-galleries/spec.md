## MODIFIED Requirements

### Requirement: Persistência do histórico privado
O sistema SHALL manter biblioteca visual para cada cliente autorizada, separando Galerias públicas, privadas compartilhadas das quais é membro e histórico individual. Bloqueio, expiração, desvinculação ou remoção operacional SHALL NOT apagar pedidos, entregas ou identificação histórica permitida.

#### Scenario: Biblioteca vazia
- **WHEN** a cliente autenticada não possui origem, associação privada ativa nem entrega histórica
- **THEN** a interface mostra estado vazio claro sem sugerir ou revelar galerias de terceiros

#### Scenario: Nova foto disponível
- **WHEN** administrador ou membro adiciona referência autorizada à privada
- **THEN** todos os membros ativos veem a foto disponível, preservando seus estados individuais

#### Scenario: Nova pasta liberada
- **WHEN** o fotógrafo libera uma nova pasta autorizada na Galeria pública de origem
- **THEN** a privada ou biblioteca apresenta as novas fotos disponíveis conforme sua organização, sem alterar seleções e compras individuais anteriores

#### Scenario: Histórico após expiração ou bloqueio
- **WHEN** a privada expira ou a cliente é bloqueada
- **THEN** a cliente continua acessando pedidos e entregas históricas permitidas sem criar nova seleção

#### Scenario: Histórico após expiração
- **WHEN** o prazo de seleção da privada expira
- **THEN** a cliente continua acessando seus pedidos, entregas e identificação de fotos compradas sem criar seleção fora das regras de reativação

### Requirement: Interface da cliente orientada pelo backend
O sistema SHALL renderizar biblioteca, associação, permissões, prazo, fotos compartilhadas e estados individuais a partir de respostas autorizadas do backend. O frontend SHALL NOT inferir vínculo por link, telefone ou estado local e SHALL NOT expor lista de membros ou atividades de terceiros.

#### Scenario: Permissão alterada
- **WHEN** o fotógrafo bloqueia, desbloqueia ou desvincula uma cliente
- **THEN** a interface representa o novo estado devolvido pelo backend sem preservar permissão local obsoleta

#### Scenario: Galeria sem associação
- **WHEN** uma cliente possui URL ou identificador de privada à qual não pertence
- **THEN** o sistema nega sem revelar existência, membros, fotos ou interações

#### Scenario: Galeria de outra responsável
- **WHEN** uma cliente possui o URL ou identificador de uma privada à qual outra cliente está associada, mas ela própria não é membro
- **THEN** a interface recebe acesso negado sem revelar metadados, membros, fotos, favoritos, comentários ou pedidos

#### Scenario: Origem ativa determina a privada
- **WHEN** a cliente entra diretamente em uma Galeria pública vinculada e inicia seleção
- **THEN** o backend cria ou reutiliza a única privada associada àquela origem e cliente sem consultar privadas de outras origens
