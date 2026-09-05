## MODIFIED Requirements

### Requirement: Persistência do histórico privado
O sistema SHALL manter biblioteca visual para cada cliente autorizada, agrupando em uma única jornada cada Galeria pública e sua privada operacional correspondente, além do histórico individual. A privada SHALL continuar existindo para administração, conteúdo preparado, seleção, checkout e contingência, mas uma privada criada automaticamente pela seleção pública SHALL NOT aparecer como um segundo card concorrente. Bloqueio, expiração, desvinculação ou remoção operacional SHALL NOT apagar pedidos, entregas ou identificação histórica permitida.

#### Scenario: Biblioteca vazia
- **WHEN** a cliente autenticada não possui origem, associação privada ativa nem entrega histórica
- **THEN** a interface mostra estado vazio claro sem sugerir ou revelar galerias de terceiros

#### Scenario: Nova foto disponível
- **WHEN** administrador ou membro adiciona referência autorizada à privada
- **THEN** todos os membros ativos veem a foto disponível, preservando seus estados individuais

#### Scenario: Nova pasta liberada
- **WHEN** o fotógrafo libera uma nova pasta autorizada na Galeria pública de origem
- **THEN** a privada ou biblioteca apresenta as novas fotos disponíveis conforme sua organização, sem alterar seleções e compras individuais anteriores

#### Scenario: Primeira seleção não duplica a jornada
- **WHEN** a cliente seleciona sua primeira foto em uma Galeria pública e o backend cria a privada operacional
- **THEN** a biblioteca mantém um único card para aquela origem, restaura a seleção na Galeria pública e não apresenta a privada automática como outra galeria equivalente

#### Scenario: Conteúdo preparado pelo fotógrafo
- **WHEN** o fotógrafo adiciona fotos ao acervo privado de uma cliente cuja Galeria pública permanece disponível
- **THEN** a biblioteca apresenta `Fotos preparadas para você` dentro da mesma jornada da origem, sem criar um segundo card de evento

#### Scenario: Entrada direta pela privada
- **WHEN** uma cliente abre um link privado válido e possui associação ativa
- **THEN** o sistema abre a superfície privada autorizada sem exigir passagem prévia pela biblioteca e sem conceder acesso a outra privada

#### Scenario: Origem indisponível com privada preservada
- **WHEN** a Galeria pública fica removida ou indisponível e a cliente ainda possui acesso operacional à privada preservada
- **THEN** a biblioteca mantém uma única jornada, usa a privada como superfície de contingência e explica que a origem pública não está disponível

#### Scenario: Histórico após expiração ou bloqueio
- **WHEN** a privada expira ou a cliente é bloqueada
- **THEN** a cliente continua acessando pedidos e entregas históricas permitidas sem criar nova seleção

#### Scenario: Histórico após expiração
- **WHEN** o prazo de seleção da privada expira
- **THEN** a cliente continua acessando seus pedidos, entregas e identificação de fotos compradas sem criar seleção fora das regras de reativação

### Requirement: Interface da cliente orientada pelo backend
O sistema SHALL renderizar jornadas agrupadas, associação, permissões, prazo, fotos compartilhadas e estados individuais a partir de respostas autorizadas do backend. O frontend SHALL NOT inferir agrupamento, vínculo, superfície principal ou contingência por link, telefone ou estado local e SHALL NOT expor lista de membros ou atividades de terceiros.

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
