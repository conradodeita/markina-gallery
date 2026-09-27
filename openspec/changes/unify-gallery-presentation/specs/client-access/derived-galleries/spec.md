## MODIFIED Requirements

> **Supersession:** a composição visual e os limites de autorização permanecem válidos. A biblioteca passa a incluir Galerias públicas autenticadas, privadas e histórico conforme `improve-gallery-and-client-data-lifecycle`; este delta SHALL NOT ser reaplicado para ocultar uma Galeria pública autorizada.

### Requirement: Interface da cliente orientada pelo backend

O sistema SHALL renderizar biblioteca, pastas, propriedade, permissões, prazo, interações, estados das fotos e histórico da cliente a partir de respostas autorizadas do backend. A galeria privada SHALL usar a mesma composição visual base da prévia do fotógrafo, adaptada ao conjunto de pastas liberadas e fotos atribuídas. A composição compartilhada SHALL NOT fazer o frontend inferir vínculo, revelar a galeria-mãe ou exibir conteúdo não autorizado.

#### Scenario: Permissão alterada

- **WHEN** o fotógrafo altera acesso, prazo, permissões ou liberação de uma galeria derivada
- **THEN** a cliente vê o novo estado retornado pelo backend sem o frontend conceder ou preservar permissão localmente

#### Scenario: Galeria de outra responsável

- **WHEN** uma cliente possui o URL ou identificador de uma galeria pertencente a outra responsável
- **THEN** a interface recebe somente resposta de acesso negado e não exibe metadados, fotos, favoritos, comentários ou pedidos dessa galeria

#### Scenario: Cliente abre galeria autorizada

- **WHEN** a cliente autenticada abre uma galeria privada ativa
- **THEN** ela vê capa, navegação por pastas, grade e visualizador na mesma hierarquia visual da prévia do fotógrafo, restritos às suas prévias autorizadas

#### Scenario: Conteúdo não liberado

- **WHEN** uma pasta ou foto não está liberada para a cliente
- **THEN** a composição compartilhada não a apresenta nem indica sua existência

#### Scenario: Cliente tenta copiar uma prévia

- **WHEN** a cliente tenta arrastar, abrir o menu de contexto ou copiar uma imagem protegida pela interface
- **THEN** o navegador bloqueia a interação comum, mantém a prévia incorporada com marca-d’água e apresenta uma mensagem acessível de conteúdo protegido

#### Scenario: Cliente aciona uma captura de tela detectável

- **WHEN** o navegador informa uma tentativa pela tecla `PrintScreen`
- **THEN** a interface apresenta o aviso de proteção sem afirmar que a captura do sistema operacional foi impedida

#### Scenario: Navegador solicita a imagem exibida

- **WHEN** a galeria renderiza capa, grade ou visualizador
- **THEN** o navegador recebe somente a prévia autenticada, limitada e já marcada pelo servidor, nunca o original nem uma proteção dependente apenas de CSS

#### Scenario: Navegação sem Minha galeria
- **WHEN** uma cliente autenticada acessa sua galeria canônica
- **THEN** a Coleção oferece seleção, favoritos, comentários e pedido de novo prazo; o Carrinho oferece revisão e PIX; Compras oferece pedidos, estados de pagamento e entregas, sem botão ou página operacional “Minha galeria”

#### Scenario: Link legado da galeria privada
- **WHEN** uma cliente abre um link antigo de “Minha galeria”
- **THEN** o sistema verifica autenticação e vínculo antes de redirecionar à Coleção ou a Compras conforme o contexto, sem revelar dados de outra cliente

#### Scenario: Tentativa de criar galeria ou link privado novo
- **WHEN** uma chamada administrativa antiga tenta criar uma galeria derivada, emitir ou rotacionar seu link privado
- **THEN** o backend recusa a operação sem gravar a derivada ou capacidade nova; o vínculo simples da cliente com a galeria pública continua disponível

#### Scenario: Exportação individual após a unificação
- **WHEN** o fotógrafo exporta a seleção ou as compras de uma cliente no card da galeria canônica
- **THEN** o arquivo contém somente dados daquela cliente, as fotos selecionadas seguem o público atual e as compras confirmadas usam seus snapshots históricos, inclusive as legadas permitidas
