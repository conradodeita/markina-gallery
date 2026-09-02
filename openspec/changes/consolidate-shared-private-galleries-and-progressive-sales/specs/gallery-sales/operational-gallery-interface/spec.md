## MODIFIED Requirements

### Requirement: Operação administrativa de galerias privadas
O sistema SHALL fornecer ao fotógrafo interface para criar e operar Galerias públicas, privadas compartilhadas, membros, pastas e JPEGs. A etapa Clientes SHALL permitir criar ou reutilizar uma privada, gerenciar seu link estável, adicionar fotos e membros e bloquear, desbloquear ou desvincular cada cliente sem expor acervos antes da autorização.

#### Scenario: Criação guiada
- **WHEN** o fotógrafo conclui fluxo válido
- **THEN** o sistema cria somente entidades e referências necessárias e apresenta confirmação ou erro acessível

#### Scenario: Segundo cliente
- **WHEN** o fotógrafo adiciona outra cliente à privada e ela não possui associação privada naquela origem
- **THEN** o sistema cria um membro com estado comercial vazio na mesma privada sem alterar os demais

#### Scenario: Segunda responsável
- **WHEN** o fotógrafo vincula uma nova cliente a uma privada compartilhada e ela não possui outro vínculo privado naquela origem
- **THEN** o sistema cria uma associação na mesma privada com seleção, prazo individual aplicável, pedido e histórico vazios, sem alterar os membros existentes

#### Scenario: Cliente já vinculada em outra privada
- **WHEN** o fotógrafo tenta adicionar telefone já associado a outra privada da mesma Galeria pública
- **THEN** o backend rejeita a duplicação e oferece acesso ao vínculo existente sem transferir histórico automaticamente

#### Scenario: Pasta em preparação
- **WHEN** o fotógrafo abre pasta ainda não publicada
- **THEN** ele vê JPEGs, processamento e ações administrativas sem expor esse conteúdo à cliente

#### Scenario: Proteção do acervo
- **WHEN** uma cliente acessa a interface
- **THEN** o sistema não revela controles administrativos, membros ou fotos fora de suas galerias autorizadas

### Requirement: Exclusão segura de galeria privada
O sistema SHALL permitir exclusão operacional da privada independentemente de vínculos e fotos removíveis, mediante inventário e política comercial. A operação SHALL preservar clientes, pedidos, pagamentos, entregas, snapshots e mídia histórica; itens com pagamento em análise SHALL bloquear somente a parte afetada até decisão.

#### Scenario: Privada sem compra
- **WHEN** o fotógrafo confirma exclusão de privada sem impedimento comercial
- **THEN** o sistema revoga link e acessos, remove referências operacionais elegíveis e preserva identidades e outras galerias

#### Scenario: Histórico de compra preservado
- **WHEN** a privada possui pedido confirmado com histórico materializado
- **THEN** a operação remove a superfície operacional sem alterar pedido, itens, valores, entregas ou consulta histórica

## ADDED Requirements

### Requirement: Persistência ao navegar no editor
As etapas editáveis SHALL salvar e validar seus dados antes de avançar. A interface SHALL navegar somente após sucesso, permanecer na etapa diante de erro e impedir perda silenciosa por rodapé, stepper ou retorno quando houver alterações pendentes.

#### Scenario: Salvar e avançar
- **WHEN** o fotógrafo altera Vendas ou Detalhes e aciona `Salvar e avançar`
- **THEN** a aplicação aguarda a persistência, mostra erro sem navegar em caso de falha ou abre a etapa seguinte em caso de sucesso

#### Scenario: Troca direta de etapa
- **WHEN** existem alterações não salvas e o fotógrafo aciona outra etapa
- **THEN** a interface salva com sucesso antes da troca ou solicita confirmação para descartar, sem perder dados silenciosamente

### Requirement: Links administráveis e estáveis
O sistema SHALL apresentar na etapa Clientes o link compartilhável vigente da Galeria pública e de cada privada, com copiar, revogar e regenerar. O endereço SHALL permanecer estável durante uso normal; regenerar SHALL invalidar o anterior e exigir confirmação sobre o impacto.

#### Scenario: Galeria recém-criada
- **WHEN** o backend cria a Galeria pública
- **THEN** a etapa Clientes consegue apresentar e copiar seu link sem descartar o segredo durante o redirecionamento do assistente

#### Scenario: Link privado regenerado
- **WHEN** o fotógrafo confirma regeneração por incidente
- **THEN** o endereço anterior deixa de criar vínculos, membros atuais permanecem e o novo link passa a ser copiável

### Requirement: Configuração comercial integrada
O editor SHALL apresentar escolha entre preço fixo e tabela global progressiva, campos de moeda brasileira, prévia de cálculo e PIX copia-e-cola com QR gerado. O botão de avanço SHALL persistir toda a configuração sem criar ou alterar pedido existente.

#### Scenario: Vendas progressivas
- **WHEN** o fotógrafo escolhe uma tabela e simula uma quantidade
- **THEN** a etapa mostra parcelas, total e economia retornados pelo backend antes de salvar

#### Scenario: PIX válido
- **WHEN** o fotógrafo informa código PIX copia-e-cola válido
- **THEN** a prévia apresenta QR correspondente e o backend salva somente código e instruções necessários
