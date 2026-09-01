## MODIFIED Requirements

### Requirement: Configuração visual e marca-d’água

O sistema SHALL permitir ao fotógrafo configurar globalmente texto, tipografia, cor, tamanho e direção suportada da marca-d’água antes de gerar novas prévias. A Galeria pública SHALL permitir configurar capa, título e uma tipografia de título escolhida de lista segura com famílias neutras, editoriais e manuscritas empacotadas pela aplicação. A organização das pastas SHALL ser configurada na etapa Imagens e pastas. Nenhum campo SHALL aceitar fonte remota, CSS livre ou família arbitrária fornecida pelo navegador.

#### Scenario: Carregamento direto

- **WHEN** o fotógrafo clica em “Carregar fotos” dentro de uma pasta
- **THEN** o seletor local abre e os JPEGs escolhidos são registrados naquela pasta para processamento

#### Scenario: Tipografia manuscrita

- **WHEN** o fotógrafo escolhe uma tipografia manuscrita suportada para o título
- **THEN** a prévia e a galeria entregue usam a mesma família local com fallback legível, sem buscar recurso em domínio externo

#### Scenario: Valor de fonte não permitido

- **WHEN** uma requisição tenta persistir uma família fora da lista segura
- **THEN** o backend recusa o valor sem salvar CSS ou URL arbitrária

#### Scenario: Organização na etapa correta

- **WHEN** o fotógrafo abre Detalhes e apresentação
- **THEN** a etapa não apresenta Exibição das pastas, que permanece disponível na etapa Imagens e pastas

### Requirement: Visualização da galeria

O sistema SHALL permitir abrir o link opaco de uma Galeria pública e SHALL exigir autenticação antes de qualquer prévia fotográfica. Nas experiências autorizadas, fotógrafo e cliente SHALL receber uma composição responsiva com capa, pastas, grade borderless, espaçamento consistente, imagens preservadas em sua proporção e visualizador acessível. O modo de pastas lado a lado ou sequência SHALL continuar decidido pela configuração da Galeria pública e herdado pelas privadas.

#### Scenario: Modo individual

- **WHEN** a Galeria pública está configurada para pastas individuais e o papel possui autorização
- **THEN** a capa aparece primeiro e as pastas permitidas são navegáveis com nome, contagem e fotos adaptadas às próprias proporções

#### Scenario: Modo sequencial

- **WHEN** a Galeria pública está configurada para sequência e o papel possui autorização
- **THEN** a capa aparece primeiro e cada pasta permitida é exibida em ordem com título e grade contínua

#### Scenario: Smartphone

- **WHEN** a galeria é aberta em viewport móvel
- **THEN** a grade, os marcadores e o visualizador permanecem tocáveis e legíveis, sem cortar fotos nem produzir rolagem horizontal da página

#### Scenario: Estado visual da cliente

- **WHEN** uma foto está favoritada, selecionada ou comprada pela cliente
- **THEN** a imagem mantém protagonismo e apresenta indicador sobreposto e texto acessível correspondente ao estado devolvido pelo backend
