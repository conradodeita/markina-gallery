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

### Requirement: Personalização visual administrativa orientada à prévia

O sistema SHALL apresentar as configurações de marca-d’água, capa/título e organização em painéis administrativos claros, acessíveis e responsivos. Os controles SHALL usar somente valores suportados pelo backend e SHALL explicar seu efeito na prévia protegida, sem oferecer CSS, templates ou posicionamento livres.

#### Scenario: Fotógrafo ajusta marca-d’água

- **WHEN** o fotógrafo abre a personalização da galeria
- **THEN** ele encontra texto, fonte, cor, tamanho e direção agrupados em um painel de marca-d’água com orientação e prévia protegida quando disponível

#### Scenario: Prévia sem fotografia disponível

- **WHEN** não houver capa ou foto pronta para representar a personalização
- **THEN** a interface preserva os controles, informa o estado de prévia e orienta o fotógrafo a carregar ou processar uma foto, sem criar conteúdo simulado
