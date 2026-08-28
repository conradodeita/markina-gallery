## MODIFIED Requirements

### Requirement: Operação administrativa de galerias privadas

O sistema SHALL fornecer ao fotógrafo autenticado uma prévia da galeria com a mesma composição visual base usada pela cliente: capa, contexto, navegação por pastas, grade de prévias protegidas, estados e visualizador. A prévia SHALL permanecer identificada como modo fotógrafo e SHALL respeitar as permissões administrativas sem criar ou conceder autorização de cliente.

#### Scenario: Fotógrafo revisa a apresentação da galeria

- **WHEN** o fotógrafo abre a prévia de uma galeria-mãe
- **THEN** o sistema mostra uma composição visual equivalente à da galeria da cliente, usando apenas prévias protegidas e dados permitidos ao fotógrafo

#### Scenario: Galeria sem capa ou conteúdo pronto

- **WHEN** a galeria não possui capa ou ainda não possui prévias disponíveis
- **THEN** a prévia mostra um estado visual claro e orienta o fotógrafo sem apresentar uma estrutura quebrada ou conteúdo de cliente

### Requirement: Personalização visual administrativa orientada à prévia

O sistema SHALL apresentar as configurações de marca-d’água, capa/título e organização em painéis administrativos claros, acessíveis e responsivos. Os controles SHALL usar somente valores suportados pelo backend e SHALL explicar seu efeito na prévia protegida, sem oferecer CSS, templates ou posicionamento livres.

#### Scenario: Fotógrafo ajusta marca-d’água

- **WHEN** o fotógrafo abre a personalização da galeria
- **THEN** ele encontra texto, fonte, cor, tamanho e direção agrupados em um painel de marca-d’água com orientação e prévia protegida quando disponível

#### Scenario: Prévia sem fotografia disponível

- **WHEN** não houver capa ou foto pronta para representar a personalização
- **THEN** a interface preserva os controles, informa o estado de prévia e orienta o fotógrafo a carregar ou processar uma foto, sem criar conteúdo simulado
