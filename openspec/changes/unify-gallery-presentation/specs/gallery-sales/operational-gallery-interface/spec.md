## MODIFIED Requirements

### Requirement: Operação administrativa de galerias privadas

O sistema SHALL fornecer ao fotógrafo autenticado uma interface original para criar e operar clientes, acervos-fonte não listados, galerias privadas, pastas e JPEGs. A interface SHALL apresentar fluxo claro de criação, edição, preparação e liberação, sem expor acervos a clientes antes da autorização e liberação aplicáveis. A prévia administrativa SHALL usar a mesma composição visual base usada pela cliente — capa, contexto, navegação por pastas, grade de prévias protegidas, estados e visualizador — mantendo-se identificada como modo fotógrafo e sem conceder autorização de cliente.

#### Scenario: Criação guiada

- **WHEN** o fotógrafo conclui o fluxo administrativo com dados válidos
- **THEN** o sistema cria somente as referências privadas escolhidas e apresenta confirmação ou erro acessível

#### Scenario: Segunda responsável

- **WHEN** o fotógrafo vincula uma nova responsável a fotos já disponibilizadas para outra responsável
- **THEN** o sistema cria ou vincula uma galeria privada independente para a nova responsável sem alterar seleção, prazo, pedido ou histórico da primeira

#### Scenario: Pasta em preparação

- **WHEN** o fotógrafo abre uma pasta ainda não liberada
- **THEN** ele vê os JPEGs, o estado de processamento e as ações de edição ou liberação disponíveis somente para ele

#### Scenario: Proteção do acervo

- **WHEN** uma cliente acessa a interface
- **THEN** o sistema não revela controles administrativos nem fotos fora de sua galeria derivada e pastas liberadas

#### Scenario: Fotógrafo revisa a apresentação da galeria

- **WHEN** o fotógrafo abre a prévia de uma galeria-mãe
- **THEN** o sistema mostra uma composição visual equivalente à da galeria da cliente, usando apenas prévias protegidas e dados permitidos ao fotógrafo

#### Scenario: Galeria sem capa ou conteúdo pronto

- **WHEN** a galeria não possui capa ou ainda não possui prévias disponíveis
- **THEN** a prévia mostra um estado visual claro e orienta o fotógrafo sem apresentar uma estrutura quebrada ou conteúdo de cliente

## ADDED Requirements

### Requirement: Proteção visual global e organização por galeria

O sistema SHALL apresentar em Configurações os controles globais de marca-d’água e proteção visual usados por todas as prévias protegidas. Os controles SHALL usar somente valores suportados pelo backend, ter explicação e prévia acessíveis e não oferecer CSS, templates ou posicionamento livres. O editor de cada galeria SHALL manter a organização de pastas como escolha específica da galeria e não SHALL oferecer substituições locais dos valores globais de proteção.

#### Scenario: Fotógrafo ajusta a proteção visual global

- **WHEN** o fotógrafo altera texto, fonte, cor, tamanho ou direção da marca-d’água em Configurações
- **THEN** o sistema persiste os valores globais validados e as prévias protegidas entregues em qualquer galeria passam a usar essa configuração única, sem expor originais

#### Scenario: Fotógrafo organiza uma galeria

- **WHEN** o fotógrafo abre o editor de uma galeria
- **THEN** ele pode escolher a organização de pastas suportada para aquela galeria, sem receber controles locais de marca-d’água

#### Scenario: Prévia sem fotografia disponível

- **WHEN** não houver capa ou foto pronta para representar a configuração global
- **THEN** a interface preserva os controles, informa o estado de prévia e orienta o fotógrafo a carregar ou processar uma foto, sem criar conteúdo simulado
