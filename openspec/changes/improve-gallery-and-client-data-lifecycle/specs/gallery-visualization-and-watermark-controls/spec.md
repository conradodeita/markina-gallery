## MODIFIED Requirements

### Requirement: Configuração visual e marca-d’água

O sistema SHALL permitir ao fotógrafo configurar globalmente texto, tipografia, cor, tamanho e direção suportada da marca-d’água antes de gerar novas prévias. Cada Galeria pública SHALL combinar essa proteção global com capa, título, organização e demais apresentação permitida; suas galerias privadas SHALL herdar a configuração efetiva da origem sem override privado. A etapa Imagens SHALL oferecer um único comando de carregamento que abre o seletor local e envia os JPEGs escolhidos.

#### Scenario: Carregamento direto

- **WHEN** o fotógrafo clica em “Carregar fotos”
- **THEN** o seletor local é aberto e os arquivos JPEG selecionados são registrados e enviados para a pasta atual

#### Scenario: Privada representa a origem

- **WHEN** uma galeria privada é criada ou aberta depois de alteração da apresentação da Galeria pública
- **THEN** ela usa a apresentação efetiva da origem e a proteção global vigente, sem oferecer configuração visual privada divergente

### Requirement: Visualização da galeria

O sistema SHALL permitir abrir um link opaco de Galeria pública e SHALL exigir autenticação antes de qualquer prévia fotográfica. O backend SHALL decidir o modo `standard`, `invite_only` ou `collective_protected`; o fotógrafo SHALL visualizar em modo administrativo claramente indicado. Nas experiências autorizadas, o fotógrafo SHALL poder configurar pastas individuais lado a lado ou sequência cronológica, com título sobre a capa conforme a apresentação da Galeria pública, herdada pelas privadas.

#### Scenario: Modo individual

- **WHEN** a Galeria pública está configurada para pastas individuais e o papel possui autorização
- **THEN** a capa protegida é apresentada primeiro e as pastas permitidas aparecem lado a lado com nome e contagem

#### Scenario: Modo sequencial

- **WHEN** a Galeria pública está configurada para sequência e o papel possui autorização
- **THEN** a capa protegida é apresentada primeiro e cada pasta permitida é exibida em ordem com seu título antes das fotos

#### Scenario: Cliente sem autenticação

- **WHEN** uma pessoa sem sessão abre o link da Galeria pública
- **THEN** a interface pode mostrar informação não fotográfica, mas não solicita nem renderiza prévia antes do OTP

#### Scenario: Evento coletivo

- **WHEN** a Galeria pública usa `collective_protected`
- **THEN** somente o fotógrafo vê o acervo e a experiência da cliente não apresenta grade nem enumera fotos

### Requirement: Exclusão em massa elegível

O sistema SHALL permitir selecionar várias fotos operacionais e solicitar exclusão com uma única confirmação e inventário. A operação SHALL aplicar a política comercial do backend: fotos sem pedido impeditivo podem ser removidas; pedido pendente sem pagamento comunicado é cancelado com auditoria; pagamento comunicado ou `pending_review` bloqueia a foto afetada; item confirmado somente perde sua referência operacional após preparação do histórico mínimo. A exclusão SHALL informar individualmente removidas, preservadas e bloqueadas.

#### Scenario: Exclusão parcial protegida

- **WHEN** o fotógrafo seleciona fotos elegíveis e fotos relacionadas a estados comerciais impeditivos
- **THEN** o sistema exclui somente as elegíveis, preserva as bloqueadas e informa o motivo de cada resultado

#### Scenario: Foto confirmada com histórico preparado

- **WHEN** a foto integra pedido confirmado e sua evidência mínima e entrega já foram verificadas
- **THEN** a operação pode remover a mídia operacional sem alterar item, valores, cliente ou acesso histórico autorizado
