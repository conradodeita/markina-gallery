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

#### Scenario: Desvinculação em processamento ou bloqueada
- **WHEN** o fotógrafo confirma a desvinculação de uma cliente na etapa Clientes
- **THEN** a interface apresenta no próprio contexto da cliente o progresso retornado pelo backend e, diante de bloqueio comercial ou falha, explica a causa e a ação de recuperação sem aparentar inércia

#### Scenario: Nenhuma foto publicável para montar a privada
- **WHEN** o fotógrafo aciona `Montar galeria privada` e ainda não existe foto publicada elegível
- **THEN** a interface explica que a publicação deve ser concluída na etapa Imagens e oferece acesso direto a essa etapa, em vez de manter um botão silenciosamente inoperante

#### Scenario: Desvinculação de cadastro sem privada nem pedido
- **WHEN** o fotógrafo desvincula uma cliente cadastrada administrativamente que possui somente o vínculo ativo com a Galeria pública
- **THEN** o worker conclui a operação sem depender de pedido ou Galeria privada, remove somente o vínculo e preserva a identidade da cliente

### Requirement: Exclusão segura de galeria privada
O sistema SHALL permitir exclusão operacional da privada independentemente de vínculos e fotos removíveis, mediante inventário e política comercial. A operação SHALL preservar clientes, pedidos, pagamentos, entregas, snapshots e mídia histórica; itens com pagamento em análise SHALL bloquear somente a parte afetada até decisão.

#### Scenario: Privada sem compra
- **WHEN** o fotógrafo confirma exclusão de privada sem impedimento comercial
- **THEN** o sistema revoga link e acessos, remove referências operacionais elegíveis e preserva identidades e outras galerias

#### Scenario: Exclusão confirmada, bloqueada ou em processamento
- **WHEN** o fotógrafo aciona a exclusão de uma Galeria pública ou privada
- **THEN** a interface mantém confirmação, erro e progresso junto à ação, explica qualquer impedimento comercial retornado pelo backend e apresenta o próximo estado sem aparentar inércia

#### Scenario: Histórico de compra preservado
- **WHEN** a privada possui pedido confirmado com histórico materializado
- **THEN** a operação remove a superfície operacional sem alterar pedido, itens, valores, entregas ou consulta histórica

## ADDED Requirements

### Requirement: Persistência ao navegar no editor
As etapas editáveis SHALL salvar e validar seus dados antes de avançar. A interface SHALL navegar somente após sucesso, permanecer na etapa diante de erro e impedir perda silenciosa por rodapé, stepper ou retorno quando houver alterações pendentes.

#### Scenario: Salvar e avançar
- **WHEN** o fotógrafo altera Vendas ou Detalhes e aciona `Salvar e avançar`
- **THEN** a aplicação aguarda a persistência, mostra erro sem navegar em caso de falha ou abre a etapa seguinte em caso de sucesso

#### Scenario: Publicar fotos prontas ao avançar de Imagens
- **WHEN** o fotógrafo aciona `Salvar e avançar` na etapa Imagens após o processamento das prévias
- **THEN** a aplicação publica todas as fotos prontas da Galeria pública antes de abrir Clientes e permanece na etapa com contagens claras se houver foto ainda processando ou com falha

#### Scenario: Troca direta de etapa
- **WHEN** existem alterações não salvas e o fotógrafo aciona outra etapa
- **THEN** a interface salva com sucesso antes da troca ou solicita confirmação para descartar, sem perder dados silenciosamente

#### Scenario: Explicação dos modos de acesso
- **WHEN** o fotógrafo configura o modo de acesso na etapa Ajustes
- **THEN** a interface explica a consequência prática de `Padrão`, `Somente convite individual` e `Coletivo protegido`, deixando explícito que todas as prévias exigem autenticação e que o modo coletivo não habilita reconhecimento facial

### Requirement: Links administráveis e estáveis
O sistema SHALL apresentar na etapa Clientes o link compartilhável vigente da Galeria pública e de cada privada, com copiar, revogar e regenerar. O endereço SHALL permanecer estável durante uso normal; regenerar SHALL invalidar o anterior e exigir confirmação sobre o impacto.

#### Scenario: Galeria recém-criada
- **WHEN** o backend cria a Galeria pública
- **THEN** a etapa Clientes consegue apresentar e copiar seu link sem descartar o segredo durante o redirecionamento do assistente

#### Scenario: Link privado regenerado
- **WHEN** o fotógrafo confirma regeneração por incidente
- **THEN** o endereço anterior deixa de criar vínculos, membros atuais permanecem e o novo link passa a ser copiável

### Requirement: Configuração comercial integrada
O editor SHALL apresentar escolha entre preço fixo e tabela global progressiva, campos de moeda brasileira, prévia de cálculo e PIX por BR Code completo ou chave simples suportada com QR gerado. O botão de avanço SHALL persistir toda a configuração sem criar ou alterar pedido existente.

#### Scenario: Vendas progressivas
- **WHEN** o fotógrafo escolhe uma tabela e simula uma quantidade
- **THEN** a etapa mostra parcelas, total e economia retornados pelo backend antes de salvar

#### Scenario: PIX válido
- **WHEN** o fotógrafo informa código PIX copia-e-cola válido
- **THEN** a prévia apresenta QR correspondente e o backend salva somente código e instruções necessários

#### Scenario: Chave PIX simples suportada
- **WHEN** o fotógrafo informa CPF válido, telefone brasileiro ou e-mail e fornece nome e cidade públicos do recebedor
- **THEN** o backend normaliza a chave, gera localmente um BR Code estático válido, persiste a entrada estruturada para edição e devolve o QR correspondente

#### Scenario: Chave simples sem dados do recebedor
- **WHEN** o fotógrafo informa chave simples sem nome ou cidade necessários à geração do BR Code
- **THEN** a interface permanece na etapa e explica os campos necessários, sem inventar dados nem gerar QR de texto cru

### Requirement: Primeiro acesso de cliente vinculada administrativamente
O cadastro e o vínculo criados pelo fotógrafo SHALL pré-autorizar a cliente na Galeria pública, mas SHALL NOT substituir a autenticação por OTP. A interface administrativa SHALL distinguir cadastro inexistente de primeiro acesso ainda não validado.

#### Scenario: Cliente cadastrada pelo fotógrafo
- **WHEN** o fotógrafo cadastra e vincula uma cliente que ainda não autenticou o telefone
- **THEN** a cliente aparece vinculada como `Aguardando primeiro acesso`, precisa concluir o OTP ao abrir o link e, depois da validação, acessa a galeria já autorizada sem novo cadastro

### Requirement: Cadastro de clientes independente dos vínculos
O sistema SHALL manter o cadastro de cada cliente visível na busca administrativa independentemente de estar vinculado à Galeria pública ou a uma privada. A interface SHALL indicar o estado do vínculo sem retirar a cliente da lista e SHALL permitir editar nome e trocar o telefone da mesma identidade mediante comprovação OTP do novo número.

#### Scenario: Cliente já vinculada permanece na busca
- **WHEN** uma cliente retornada pela busca já possui vínculo com a Galeria pública atual
- **THEN** o card `Cadastro existente` continua exibindo nome e telefone, identifica `Já vinculada`, desabilita somente a ação redundante de vincular e mantém disponíveis as ações de edição aplicáveis

#### Scenario: Correção de nome
- **WHEN** o fotógrafo salva um novo nome válido para uma cliente
- **THEN** o backend atualiza a mesma identidade, registra auditoria e a interface recarrega o nome sem alterar vínculos ou histórico

#### Scenario: Troca de telefone
- **WHEN** o fotógrafo informa um novo telefone brasileiro único e comprova o OTP recebido nesse número
- **THEN** o backend troca o telefone ativo da mesma identidade, aposenta o número anterior e preserva galerias, pedidos e snapshots comerciais

### Requirement: Exclusão protegida de cadastro de cliente
O sistema SHALL disponibilizar exclusão administrativa de cadastro criado por engano somente quando o inventário autoritativo confirmar ausência de vínculos, sessões, desafios, interações, comunicações, pedidos, pagamentos, entregas, histórico ou outra dependência protegida. A troca de telefone SHALL usar edição da identidade e SHALL NOT exigir excluir e recadastrar a cliente.

#### Scenario: Cadastro sem dependências
- **WHEN** o fotógrafo consulta o inventário e confirma a exclusão de uma cliente sem qualquer dependência protegida
- **THEN** o backend remove o cadastro e seus telefones não verificados de forma transacional, registra auditoria sem PII e a interface retira o item da busca

#### Scenario: Cadastro com vínculo ou histórico
- **WHEN** o fotógrafo tenta excluir uma cliente com qualquer vínculo, acesso, interação, comunicação ou histórico comercial
- **THEN** o backend recusa a exclusão, informa as categorias bloqueadoras sem expor PII e orienta usar edição de telefone ou desvinculação conforme o objetivo
