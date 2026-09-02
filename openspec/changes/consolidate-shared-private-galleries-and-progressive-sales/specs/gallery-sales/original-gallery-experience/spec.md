## MODIFIED Requirements

### Requirement: Interface original por papel
O sistema SHALL fornecer interface coesa, responsiva e acessível para fotógrafo e cliente. Membros da mesma privada SHALL compartilhar a composição e o acervo, mas marcadores, comentários, seleção, valores, pagamento e histórico SHALL ser renderizados somente para a identidade autenticada.

#### Scenario: Fotógrafo inicia a operação
- **WHEN** o fotógrafo abre área administrativa ou prévia
- **THEN** ele vê contexto administrativo, membros e operações autorizadas sem executar interação em nome de cliente

#### Scenario: Cliente retoma sua jornada
- **WHEN** uma cliente abre Galeria pública ou privada autorizada
- **THEN** ela vê fotos e somente seus próprios estados comerciais, sem controles administrativos, lista de membros ou dados de terceiros

#### Scenario: Fotografias com proporções diferentes
- **WHEN** a coleção contém imagens horizontais e verticais
- **THEN** a grade preserva enquadramento, ordem acessível e ausência de overflow no smartphone

#### Scenario: Favorito ou seleção visível
- **WHEN** a cliente favorita ou seleciona uma foto
- **THEN** a apresentação mostra marcador sobreposto e texto acessível somente na sessão dela

#### Scenario: Prévia administrativa equivalente
- **WHEN** o fotógrafo abre a mesma galeria
- **THEN** a composição mantém a linguagem visual da cliente sem executar favorito, seleção ou compra

## ADDED Requirements

### Requirement: Rodapé e conferência comercial individual
Após a primeira seleção, o portal SHALL apresentar rodapé flutuante com quantidade, total autoritativo, economia e ação `Prosseguir`. A conferência SHALL listar miniaturas e nomes, gerar QR PIX, informar análise manual e permitir comunicar pagamento uma única vez.

#### Scenario: Seleção de pessoas diferentes
- **WHEN** a cliente seleciona fotos de duas pessoas na mesma privada
- **THEN** o rodapé soma todas as fotos daquela cliente e aplica uma única cotação progressiva

#### Scenario: Informar pagamento
- **WHEN** a cliente confere o pedido e aciona `Informar pagamento`
- **THEN** a interface mostra `O pagamento está em análise`, impede comunicação duplicada e aguarda decisão do fotógrafo

#### Scenario: Pagamento confirmado
- **WHEN** o fotógrafo confirma o pagamento
- **THEN** somente a cliente do pedido recebe a mensagem personalizada e os demais membros não veem valor, decisão ou compra
