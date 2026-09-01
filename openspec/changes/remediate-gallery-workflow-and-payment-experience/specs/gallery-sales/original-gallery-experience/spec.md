## MODIFIED Requirements

### Requirement: Interface original por papel

O sistema SHALL fornecer uma interface visual coesa para fotógrafo e cliente, com navegação, hierarquia, componentes e estados próprios da Markina Gallery. A apresentação da galeria SHALL ser responsiva, acessível e centrada nas fotografias, sem copiar componentes ou código de serviços concorrentes. A composição compartilhada SHALL preservar dados e ações específicos de cada papel e SHALL apresentar as fotos sem moldura de card dominante, com espaçamento uniforme e enquadramento integral adaptado às proporções horizontal e vertical.

#### Scenario: Fotógrafo inicia a operação

- **WHEN** o fotógrafo autenticado abre a área administrativa ou a prévia da Galeria pública
- **THEN** ele vê contexto administrativo claro, fotografia em destaque e somente ações permitidas ao fotógrafo

#### Scenario: Cliente retoma sua jornada

- **WHEN** uma cliente autenticada abre sua Galeria pública ou privada autorizada
- **THEN** ela vê a composição fotográfica, seus estados de seleção e histórico, sem controles administrativos ou dados de terceiros

#### Scenario: Fotografias com proporções diferentes

- **WHEN** uma coleção contém imagens horizontais e verticais
- **THEN** a grade adapta o espaço de cada item sem cortar o enquadramento, preserva ordem acessível e não cria overflow horizontal no smartphone

#### Scenario: Favorito ou seleção visível

- **WHEN** a cliente favorita ou seleciona uma foto
- **THEN** a apresentação mostra coração ou marcador equivalente sobre a foto com estado textual acessível, sem confundir a ação de ampliar

#### Scenario: Prévia administrativa equivalente

- **WHEN** o fotógrafo abre a prévia da mesma Galeria pública
- **THEN** capa, pastas, grade e visualizador mantêm a mesma linguagem visual da cliente, mas não executam favorito, seleção ou compra em nome dela
