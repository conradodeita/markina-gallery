## MODIFIED Requirements

### Requirement: Entrada por link não listado e vínculo individual

O sistema SHALL tratar o link de uma Galeria pública como localizador opaco que exige sessão de cliente e autorização do backend, não como credencial nem autorização para galerias privadas existentes. Sem sessão, o visitante SHALL concluir login por telefone e OTP antes de visualizar qualquer prévia fotográfica; com sessão válida, o sistema SHALL aplicar o modo `standard`, `invite_only` ou `collective_protected` da origem. Somente o modo `standard` SHALL vincular automaticamente o mesmo `Client` a partir do link público válido. O modo `invite_only` SHALL exigir associação ou convite individual compatível, e `collective_protected` SHALL NOT expor grade fotográfica.

#### Scenario: Cliente entra pelo link compartilhado

- **WHEN** uma pessoa sem sessão abre o link não listado de uma Galeria pública e conclui o login por OTP
- **THEN** o sistema aplica o modo de acesso no backend, cria ou reutiliza pelo telefone o vínculo somente quando autorizado, retorna à experiência permitida e não concede acesso às galerias privadas de outros clientes

#### Scenario: Evento coletivo protegido

- **WHEN** a Galeria pública representa evento coletivo protegido
- **THEN** o sistema não apresenta grade coletiva após o OTP e exige resultado facial privado, consentido e aprovado antes de criar ou exibir uma galeria privada

#### Scenario: Galeria padrão com navegação habilitada

- **WHEN** o fotógrafo define modo `standard`, publica fotos e habilita seleção manual na Galeria pública
- **THEN** a cliente autenticada pode navegar somente pelas prévias autorizadas, e sua primeira seleção inicia a galeria privada individual

#### Scenario: Galeria restrita por convite

- **WHEN** uma cliente autenticada sem associação ou convite individual válido abre o link de uma Galeria pública `invite_only`
- **THEN** o backend nega a navegação fotográfica de forma neutra e não cria vínculo automático

#### Scenario: Cliente cadastrada pelo administrador

- **WHEN** o administrador cadastra nome e telefone e associa explicitamente a cliente a uma Galeria pública
- **THEN** após validar por OTP o mesmo telefone, o sistema reutiliza o cadastro e a cliente acessa somente essa experiência autorizada, sem obter acesso a outras Galerias públicas ou privadas do banco

#### Scenario: Cliente já está autenticada

- **WHEN** uma cliente com sessão válida abre o link de outra Galeria pública ativa
- **THEN** o sistema reutiliza o mesmo `Client` sem solicitar OTP novamente, aplica o modo de acesso, vincula apenas quando autorizado e não cria galeria privada antes da primeira seleção

## ADDED Requirements

### Requirement: Derivação privada sob demanda e criação administrativa

O sistema SHALL manter no máximo uma galeria privada operacional para cada par de Galeria pública e cliente. A galeria privada SHALL ser criada atomicamente quando a cliente autenticada seleciona sua primeira foto autorizada ou quando o administrador a cria para uma cliente com ao menos uma foto disponível. O sistema SHALL distinguir referência disponível na privada de seleção para compra e SHALL registrar a origem `client`, `admin` ou origem futura explicitamente autorizada. O acesso SHALL pertencer exclusivamente à identidade de cliente vinculada ao telefone verificado.

#### Scenario: Primeira seleção da cliente

- **WHEN** uma cliente vinculada seleciona a primeira foto permitida de uma Galeria pública comum
- **THEN** o sistema cria sua galeria privada, inclui a referência disponível com origem `client` e registra a seleção como uma única operação, sem criar galeria para nenhum outro cliente

#### Scenario: Cliente seleciona foto adicional na Galeria pública

- **WHEN** uma cliente que já possui galeria privada ativa escolhe outra foto elegível na Galeria pública correspondente
- **THEN** o sistema reutiliza a mesma galeria privada, acrescenta somente a nova referência de origem `client` e a seleção e mantém a Galeria pública disponível para novas escolhas

#### Scenario: Cliente possui várias Galerias públicas

- **WHEN** uma cliente possui acesso autorizado a duas ou mais Galerias públicas abertas
- **THEN** cada seleção é encaminhada exclusivamente à galeria privada da mesma origem, sem misturar fotos, prazo, preço, pedido ou histórico entre galerias

#### Scenario: Galeria privada bloqueada ou expirada

- **WHEN** a cliente tenta selecionar nova foto na Galeria pública correspondente a uma galeria privada bloqueada ou com prazo expirado
- **THEN** o sistema rejeita a nova seleção conforme a regra operacional vigente e não cria uma segunda galeria privada para contornar o bloqueio

#### Scenario: Nova seleção após encerramento sem fotos

- **WHEN** a cliente mantém acesso à Galeria pública e seleciona uma foto depois de sua galeria privada anterior ter sido encerrada sem fotos
- **THEN** o sistema cria uma nova galeria privada operacional para o mesmo par e mantém pedidos anteriores somente no histórico independente

#### Scenario: Administrador cria galeria privada

- **WHEN** o administrador escolhe uma cliente e ao menos uma foto autorizada da Galeria pública
- **THEN** o sistema cria ou reutiliza a galeria privada exclusiva daquela cliente, adiciona referências disponíveis de origem `admin` sem criar seleções em nome dela e não altera as galerias privadas de terceiros

#### Scenario: Galeria administrativa permanece sem seleção

- **WHEN** a cliente remove ou ainda não realizou qualquer seleção, mas sua galeria privada mantém fotos disponíveis de origem `admin`
- **THEN** o sistema conserva a galeria privada e apresenta zero selecionadas sem remover as referências administrativas

#### Scenario: Cliente abre galeria criada pelo administrador

- **WHEN** a cliente abre o link da galeria privada criada pelo administrador e valida o telefone associado por OTP
- **THEN** o sistema reconhece a mesma identidade e concede acesso somente àquela galeria privada e às demais galerias que pertençam ao mesmo `Client`

#### Scenario: Administrador tenta criar galeria vazia

- **WHEN** o administrador solicita uma nova galeria privada sem escolher foto alguma
- **THEN** o sistema mantém somente o cadastro ou vínculo da cliente e não persiste uma galeria privada vazia

#### Scenario: Acesso com link de outra cliente

- **WHEN** uma cliente autenticada apresenta o link ou identificador de uma galeria privada pertencente a outra identidade
- **THEN** o sistema nega acesso sem revelar existência, fotos, seleções ou compras da proprietária

#### Scenario: Terceiro possui o link privado

- **WHEN** uma pessoa possui o link de uma galeria privada, mas valida telefone que não pertence à cliente proprietária
- **THEN** o sistema nega acesso porque a posse do link isoladamente não transfere a propriedade da galeria

#### Scenario: Resultado facial futuro aprovado

- **WHEN** uma implementação facial futura estiver habilitada após spike, consentimento e aprovação e produzir fotos autorizadas para uma cliente
- **THEN** o sistema reutiliza a mesma derivação individual sem expor a grade da Galeria pública

### Requirement: Encerramento seguro da galeria privada sem referências disponíveis

O sistema SHALL remover automaticamente uma galeria privada derivada pela cliente somente quando, depois da mutação autorizada, não restar referência disponível nem impedimento comercial. A remoção SHALL preservar cadastro, vínculo com a Galeria pública e histórico comercial independente, SHALL apagar somente estados privados não comerciais e SHALL NOT apagar o `PhotoAsset` da Galeria pública. Referência de origem `admin` SHALL sobreviver à retirada de uma seleção.

#### Scenario: Cliente remove a última foto

- **WHEN** a cliente remove a única seleção e a única referência disponível, ambas de origem `client`, sem pedido impeditivo
- **THEN** o sistema remove a galeria privada e seus estados não comerciais, mantém a cliente apta a iniciar nova seleção e não remove o arquivo da Galeria pública

#### Scenario: Última seleção usa foto disponibilizada pelo administrador

- **WHEN** a cliente retira a última seleção de uma foto cuja referência disponível tem origem `admin`
- **THEN** o sistema mantém a galeria privada e a foto disponível com zero seleções

#### Scenario: Última foto possui compra concluída

- **WHEN** a cliente remove a última referência operacional associada a item comercial confirmado
- **THEN** o sistema somente encerra a galeria depois de verificar snapshots, prévia histórica mínima e entrega ou referência final, mantendo a compra na área de histórico

#### Scenario: Pagamento está em revisão

- **WHEN** a cliente tenta remover seleção ou referência necessária a pedido com pagamento comunicado ou `pending_review`
- **THEN** o sistema bloqueia a remoção afetada até decisão administrativa e preserva o estado comercial auditável

#### Scenario: Ainda restam fotos privadas

- **WHEN** a cliente remove uma seleção, mas outra referência disponível permanece em sua galeria privada
- **THEN** o sistema mantém a galeria privada ativa somente com as referências restantes

#### Scenario: Galeria pública permanece acessível

- **WHEN** a galeria privada é encerrada porque não restou referência disponível de origem `client`, mas o vínculo e a Galeria pública continuam ativos
- **THEN** a cliente continua vendo a Galeria pública e pode iniciar uma nova derivação por seleção posterior

### Requirement: Herança da configuração da Galeria pública

O sistema SHALL usar a Galeria pública como fonte da configuração de preço e faixas, PIX, mensagens, favoritos, comentários, apresentação visual e prazo padrão de seleção de suas galerias privadas. A galeria privada SHALL NOT aceitar overrides arbitrários desses campos nesta change. O prazo efetivo SHALL ser materializado na criação da privada, e os termos comerciais SHALL ser congelados em snapshot no pedido.

#### Scenario: Administrador cria galeria privada

- **WHEN** o administrador deriva uma galeria privada de uma Galeria pública configurada
- **THEN** a privada recebe o prazo efetivo e usa apresentação, interações e configuração comercial da origem sem exigir nova configuração

#### Scenario: Configuração comercial muda antes do pedido

- **WHEN** o fotógrafo altera preço ou PIX da Galeria pública antes de a cliente concluir o checkout
- **THEN** a privada usa a configuração vigente da origem até o checkout, e o pedido concluído preserva seu próprio snapshot imutável

#### Scenario: Configuração muda depois do pedido

- **WHEN** o fotógrafo altera a Galeria pública depois de existir pedido
- **THEN** o histórico do pedido não muda, mesmo que a experiência operacional ainda aberta passe a representar a apresentação vigente da origem

### Requirement: Convites e links privados seguros

O sistema SHALL emitir tokens opacos de alta entropia para links compartilháveis e convites individuais, armazenar somente seu hash e registrar escopo, estado, expiração opcional, rotação, revogação e auditoria. A posse do token SHALL NOT substituir OTP nem permitir que telefone diferente assuma a identidade destinatária.

#### Scenario: Convite individual válido

- **WHEN** a cliente abre convite individual ativo e valida por OTP o telefone da identidade destinatária
- **THEN** o sistema consome ou registra o uso conforme a política, concede somente o escopo autorizado e não expõe o token em logs ou banco

#### Scenario: Convite revogado ou expirado

- **WHEN** alguém apresenta token revogado, expirado ou rotacionado
- **THEN** o sistema responde de forma neutra, não cria vínculo e audita a tentativa sem persistir o token em claro

#### Scenario: UUID sem token

- **WHEN** alguém conhece apenas o identificador público de uma galeria
- **THEN** o sistema não o trata como autoridade e não entrega fotografias nem dados privados

### Requirement: Desvinculação de cliente da Galeria pública

O sistema SHALL permitir ao fotógrafo desvincular uma cliente de uma Galeria pública sem excluir o cadastro da cliente nem seu histórico comercial. A desvinculação SHALL revogar o acesso operacional derivado dessa relação e SHALL NOT alterar galerias independentes da mesma cliente.

#### Scenario: Cliente sem compra é desvinculada

- **WHEN** o fotógrafo confirma a desvinculação de uma cliente que possui seleção ou interações não compradas
- **THEN** o sistema remove o vínculo e o acesso operacional correspondente, descarta os estados não comerciais dessa relação e mantém o cadastro da cliente

#### Scenario: Cliente com compra é desvinculada

- **WHEN** o fotógrafo confirma a desvinculação de uma cliente com pedido ou pagamento registrado
- **THEN** o sistema remove o vínculo e o acesso operacional, mantém o cadastro da cliente e preserva integralmente o histórico comercial para ambas as partes

#### Scenario: Cliente possui outras galerias

- **WHEN** uma cliente desvinculada ainda possui relação autorizada com outra Galeria pública
- **THEN** o sistema preserva o acesso, as seleções e o histórico da outra relação sem alteração
