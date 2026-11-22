# media-storage/gallery-media-archive Specification

## ADDED Requirements

### Requirement: Suspensão pausa novos claims de transferência

O worker SHALL exigir tenant ativo para reivindicar uma operação enfileirada ou retomar um lease expirado. SHALL preservar os estágios, reservas e operações do tenant suspenso, sem iniciar nova transferência nem reivindicar novamente o lease durante a suspensão.

#### Scenario: Job enfileirado antes da suspensão

- **WHEN** o tenant é suspenso antes de o worker reivindicar o job
- **THEN** o job permanece inalterado e o worker pode selecionar jobs de tenants ativos

#### Scenario: Lease global expirado de tenant suspenso

- **WHEN** a operação global em processamento pertence a tenant suspenso e seu lease expira
- **THEN** o worker não retoma nem substitui o lease e preserva a coordenação até a reativação
- **AND** após a reativação a mesma operação pode ser retomada com novo token e estágio preservado

### Requirement: Interfaces de arquivo e prazo são responsivas e coerentes

As interfaces de prazo, estado da pasta, recuperação e histórico SHALL usar os tokens visuais existentes, margens alinhadas e campos legíveis em celular, tablet e desktop. SHALL NOT produzir overflow horizontal da página nem indicar mídia fria ou acesso expirado como disponível ao cliente.

#### Scenario: Fotógrafo usa celular, tablet ou desktop

- **WHEN** abre formulários e cards em larguras de 390, 768 ou 1440 pixels
- **THEN** campos, avisos e ações permanecem alinhados, legíveis e operáveis por toque sem ultrapassar a largura da página

#### Scenario: Pasta indisponível aparece no painel

- **WHEN** a pasta está expirada ou no arquivo frio
- **THEN** os resumos distinguem publicação de prévias, prazo de acesso e disponibilidade física sem rótulos contraditórios

#### Scenario: O prazo vence enquanto a tela administrativa permanece aberta

- **WHEN** o fotógrafo mantém aberta uma tela administrativa com o resumo de uma pasta e o prazo de acesso vence
- **THEN** o resumo atualiza o rótulo para `Prazo de acesso encerrado` sem exigir recarga manual; ao retornar à tela após ela ficar em segundo plano, o estado temporal é reavaliado

### Requirement: Recuperação atualiza andamento e carteira na tela

A tela SHALL atualizar pedidos em fila ou processamento e reconciliar o resumo da carteira e o histórico quando mudar o estado da recuperação, sem exigir recarga manual. Uma falha de consulta SHALL apresentar erro e interromper a consulta periódica até nova ação, sem repetir a solicitação de recuperação.

#### Scenario: Recuperação termina com a tela aberta

- **WHEN** um pedido em andamento termina após a solicitação
- **THEN** a tela apresenta o resultado e atualiza reserva, débito e saldo, sem criar outro pedido

#### Scenario: Prazo e idempotência da recuperação permanecem ligados à mesma intenção

- **WHEN** o fotógrafo solicita recuperar uma pasta e a resposta ainda está pendente
- **THEN** o seletor de prazo daquela pasta permanece desabilitado até a resposta
- **AND** uma repetição com o mesmo ciclo e prazo reutiliza a mesma chave idempotente, enquanto outro prazo usa uma chave diferente e a API continua impedindo operações simultâneas para o ciclo

#### Scenario: Valores da taxa ficam estáveis durante o salvamento

- **WHEN** o proprietário salva a taxa global de recuperação e aguarda a resposta
- **THEN** taxa, senha e TOTP permanecem desabilitados até a resposta, preservando o valor que será aplicado e evitando apagar uma nova edição sem aviso

### Requirement: Expiração, arquivo e exclusão são operações separadas

O sistema SHALL tratar expiração, arquivo externo e exclusão explícita como operações distintas, com identificadores, estados e auditoria próprios. O arquivo frio MUST NOT ser removido automaticamente por idade ou encerramento de conta nesta versão.

#### Scenario: Operação de arquivo não é exclusão

- **WHEN** uma mídia entra no ciclo de arquivo frio
- **THEN** o sistema usa estados e auditoria de arquivo próprios, sem iniciar a exclusão administrativa explícita

### Requirement: Solicitação explícita validada remove a cópia fria

Quando uma solicitação explícita e validada determinar a exclusão de mídia arquivada, o sistema SHALL remover os objetos frios correspondentes por operação auditada e impedir a recuperação do ciclo após a confirmação do provedor. O sistema SHALL NOT marcar a solicitação concluída antes de verificar a remoção.

#### Scenario: Exclusão explícita da mídia arquivada

- **WHEN** uma solicitação explícita validada abrange mídia arquivada
- **THEN** o sistema executa a remoção remota auditada para os objetos abrangidos, sem aplicar uma regra automática de retenção por idade

#### Scenario: Remoção remota não foi confirmada

- **WHEN** a chamada de remoção falha ou o resultado é indeterminado
- **THEN** a solicitação não é marcada concluída e o sistema conserva estado auditável para reconciliação, impedindo uma restauração concorrente até resolver o estado

#### Scenario: Ciclo frio removido

- **WHEN** o provedor confirma a remoção de todos os objetos frios abrangidos
- **THEN** o sistema marca a exclusão concluída e rejeita pedidos de restauração daquele ciclo

### Requirement: Arquivo frio mantém isolamento por tenant

O armazenamento de mídia fria SHALL manter objetos privados e tenant-scoped. A hierarquia remota SHALL NOT substituir autorização: o servidor MUST conferir tenant e ownership antes de resolver, listar, transferir ou restaurar. O sistema SHALL NOT entregar links diretos do Drive ao fotógrafo ou cliente.

#### Scenario: Tenant acessa operação de seu arquivo

- **WHEN** um tenant autenticado solicita operação sobre uma pasta arquivada de sua propriedade
- **THEN** o backend resolve a pasta remota a partir do vínculo local validado entre tenant, galeria, pasta e ciclo

#### Scenario: Tenant tenta acessar arquivo de outro tenant

- **WHEN** um tenant solicita objeto, pasta ou operação vinculada a outro tenant, mesmo que informe identificador válido
- **THEN** o sistema nega a operação antes de consultar ou revelar metadados do objeto remoto

#### Scenario: Objeto é resolvido na hierarquia aprovada

- **WHEN** o backend transfere um objeto cujo tenant, galeria, pasta, ciclo e objeto foram validados localmente
- **THEN** resolve cada pasta filha sob o pai remoto validado, usando somente o UUID do respectivo nível e `appProperties` privadas coerentes
- **AND** confere a pasta do ciclo como pai do objeto antes de aceitar metadados ou bytes

### Requirement: Hierarquia remota do arquivo frio usa UUIDs

O armazenamento SHALL organizar os objetos sob raiz → tenant → galeria → pasta → ciclo. Cada nível SHALL usar UUID canônico, manter o pai esperado e registrar `appProperties` privadas coerentes. Arquivos SHALL ficar sob a pasta do ciclo. Nomes de marca, cliente, telefone, e-mail ou filename MUST NOT ser usados em nomes remotos.

#### Scenario: Cadeia remota validada

- **WHEN** o adapter cria ou resolve o caminho remoto para um objeto autorizado
- **THEN** cada pasta filha fica sob o pai correto e seu UUID/confirmação privada corresponde ao registro local
- **AND** o objeto fica sob o ciclo associado à galeria e pasta autorizadas

### Requirement: Busca do catálogo Drive completa e não ambígua

O adaptador SHALL solicitar o indicador `incompleteSearch` em toda busca de arquivos e SHALL aceitar a resposta somente quando ele for explicitamente `false`, `files` tiver formato válido e não houver paginação inesperada. Busca incompleta, indicador ausente/inválido, página inesperada, duplicidade ou metadados incompatíveis MUST falhar fechado e gerar erro sanitizado. O resultado MUST NOT comprovar ausência, autorizar upload, atestar ownership ou confirmar exclusão.

#### Scenario: Busca incompleta não comprova ausência

- **WHEN** o Drive retorna `files=[]` e `incompleteSearch=true` durante busca de pasta ou retry de objeto
- **THEN** o adaptador falha com conflito sanitizado antes de criar pasta, iniciar upload ou declarar objeto ausente

#### Scenario: Busca incompleta não permite concluir exclusão

- **WHEN** o Drive retorna busca incompleta ao resolver o tenant ou a cadeia de ownership de um objeto para exclusão
- **THEN** o adaptador falha fechado e não envia pedido de exclusão

#### Scenario: Paginação ou duplicidade inesperada

- **WHEN** a busca inclui `nextPageToken`, excede o limite consultado ou retorna múltiplos objetos/pastas para uma identidade única
- **THEN** o adaptador exige reconciliação e não envia nem remove objeto remoto

### Requirement: Composição do executor com o adaptador Drive preserva a medição

O adapter SHALL permitir que o executor verifique e envie um stream sem duplicar a medição de tamanho/SHA-256. Rewind ao byte zero SHALL reiniciar a medição; leituras SHALL renovar o lease e usar memória limitada. Sucesso em retry exige readback integral.

#### Scenario: Novo upload pela composição real

- **WHEN** o executor envia uma fonte sintética pelo adaptador Google Drive
- **THEN** o upload consome bytes a partir do início, tamanho e SHA-256 conferem uma única passagem de upload e a renovação do lease continua ativa

#### Scenario: Retry após perda da confirmação

- **WHEN** o upload remoto foi concluído, a confirmação se perdeu e uma nova chamada idempotente usa a mesma chave
- **THEN** o adaptador encontra e valida o mesmo objeto sem iniciar outro upload
- **AND** quando a execução recebe esse objeto, o executor lê os bytes integralmente e só então conclui o ciclo com tamanho e SHA-256 do snapshot

### Requirement: A configuração real do Drive ocorre após a entrada em produção

A configuração e os testes reais do Drive SHALL ocorrer somente depois da entrada autorizada do sistema em produção. A fase inicial de produção SHALL usar a conta do proprietário como fotógrafo; a liberação de outros tenants SHALL permanecer fechada até a validação descrita nesta change. Esta regra não altera a mudança separada de backup global do banco.

#### Scenario: Desenvolvimento local não chama o Drive

- **WHEN** o sistema ainda está em desenvolvimento local, sem entrada autorizada em produção
- **THEN** usa somente adapters sintéticos e não configura credenciais nem cria/consulta objetos reais do Drive

#### Scenario: Teste local do adaptador provider-specific

- **WHEN** testes unitários exercitam o adaptador Google Drive antes da configuração autorizada em produção
- **THEN** todas as respostas HTTP vêm de transporte sintético, nenhuma chamada de rede ou credencial real é usada e a composição normal do worker continua selecionando o adapter sintético

#### Scenario: Produção começa apenas com o proprietário

- **WHEN** a versão autorizada entra em produção e o ensaio do proprietário ainda não passou
- **THEN** outros fotógrafos/tenants não podem se cadastrar nem usar o sistema

### Requirement: A validação do proprietário cobre sua mídia antes dos tenants

Antes de liberar qualquer tenant além do proprietário, o sistema SHALL validar arquivo e recuperação completos numa galeria sintética do próprio tenant UUID do proprietário. A mídia do proprietário SHALL receber a mesma cobertura de arquivo frio, recuperação e cópia de segurança de mídia dos tenants, mantendo a isenção de créditos. O teste SHALL incluir readback e conferência de manifesto/checksums e SHALL NOT usar fotos de clientes.

#### Scenario: Proprietário conclui o teste real antes dos tenants

- **WHEN** a identidade e raiz dedicadas, permissões e quota foram verificadas e o proprietário testa arquivo, readback, recuperação e integridade de sua galeria sintética
- **THEN** o resultado completo e bem-sucedido libera o gate para outros tenants

#### Scenario: Teste real falha

- **WHEN** qualquer etapa de configuração, arquivo, readback, recuperação ou integridade falha ou fica inconclusiva
- **THEN** o sistema mantém bloqueado o acesso de outros tenants ao serviço de arquivo e recuperação até resolução e repetição bem-sucedida do ensaio

#### Scenario: Mídia do proprietário é arquivada

- **WHEN** uma pasta de conteúdo do próprio tenant do proprietário fica elegível para arquivo
- **THEN** aplica-se o mesmo ciclo, isolamento e recuperação usados para tenants, sem débito de créditos do proprietário

### Requirement: Elegibilidade ao arquivo é controlada por pasta

A expiração que controla o arquivo SHALL pertencer à pasta de conteúdo, pública ou privada, e não à galeria. A janela antes da elegibilidade SHALL começar na expiração efetiva da pasta e durar 30 dias corridos completos.

#### Scenario: Pasta expirada dentro da janela

- **WHEN** uma pasta pública ou privada expirou e ainda está dentro dos 30 dias corridos completos, contados desde sua expiração efetiva
- **THEN** o sistema não inicia transferência nem remoção primária e mostra prazo e estado ao fotógrafo

#### Scenario: Pasta elegível sem pedido em aberto

- **WHEN** os 30 dias corridos completos após a expiração da pasta terminar e não houver pedido aguardando pagamento, produção/edição ou entrega
- **THEN** a pasta fica elegível ao arquivo mesmo que existam carrinhos ou seleções em aberto

### Requirement: Arquivamento elegível entra automaticamente na fila

O sistema SHALL descobrir periodicamente pastas que completaram a janela de 30 dias e criar, sem ação do fotógrafo, um ciclo e uma operação durável de arquivo. A descoberta SHALL revalidar o prazo efetivo da pasta, inclusive a reabertura privada mais recente, e os bloqueios de pedido e trabalho de mídia. Repetir a descoberta SHALL NOT criar ciclos ou operações duplicados. Pasta bloqueada permanece local e será reavaliada em uma varredura posterior.

#### Scenario: Pasta elegível sem bloqueios entra na fila

- **WHEN** a varredura encontra uma pasta cuja janela terminou e sem pedido ou trabalho de mídia em aberto
- **THEN** cria uma única operação de arquivo para o ciclo da pasta, que passa a aguardar a transferência global

#### Scenario: Varreduras repetidas não duplicam o ciclo

- **WHEN** a mesma pasta elegível é encontrada por workers concorrentes ou em varreduras posteriores
- **THEN** o sistema mantém um único ciclo/operação ativa para aquela etapa de arquivo

#### Scenario: Bloqueio termina depois da elegibilidade

- **WHEN** havia pedido aberto na última verificação e todos os bloqueios são encerrados
- **THEN** uma varredura posterior pode enfileirar o arquivo, sem apagar mídia antes da conclusão segura

### Requirement: Expiração bloqueia navegação e novas seleções

Após o vencimento, o sistema SHALL bloquear a navegação geral da pasta e novas seleções durante a janela de 30 dias e depois dela.

#### Scenario: Cliente tenta navegar ou selecionar após o vencimento

- **WHEN** a pasta expirou e a cliente abre a listagem ou tenta selecionar uma foto
- **THEN** a listagem não revela fotos e a nova seleção é recusada

### Requirement: Prévia pós-vencimento fica limitada à seleção anterior

Durante os 30 dias corridos após a expiração, a cliente autenticada SHALL visualizar somente prévias de fotos selecionadas até o vencimento. Cada requisição MUST revalidar cliente, tenant, escopo da pasta, horário da seleção e disponibilidade local da mídia.

#### Scenario: Cliente consulta item selecionado antes do vencimento

- **WHEN** uma pasta expirou, ainda está na janela de 30 dias e a cliente havia selecionado a foto até o vencimento
- **THEN** a cliente pode abrir a prévia protegida dessa foto

#### Scenario: Cliente não consulta foto não selecionada

- **WHEN** uma pasta expirou e ainda está na janela de 30 dias, mas a cliente não selecionou a foto até o vencimento
- **THEN** o sistema não emite nem aceita URL de prévia para essa foto

#### Scenario: A janela termina exatamente após 30 dias completos

- **WHEN** a prévia é solicitada no último instante da janela
- **THEN** a seleção anterior ainda pode ser visualizada; um pedido posterior ao fim da janela não recebe essa exceção

### Requirement: Checkout na janela usa somente seleção anterior

Durante os 30 dias corridos após o vencimento, o sistema SHALL permitir checkout apenas dos itens selecionados até a expiração efetiva da pasta.

#### Scenario: Cliente conclui checkout de seleção existente

- **WHEN** a pasta expirou, ainda está na janela e o carrinho contém itens selecionados antes do vencimento
- **THEN** a cliente pode concluir checkout desses itens, sem navegar na pasta ou adicionar fotos

#### Scenario: Seleção feita após o vencimento não pode ser comprada

- **WHEN** a seleção foi criada após o vencimento ou o checkout é tentado depois da janela sem pedido já aberto
- **THEN** o sistema recusa o checkout

#### Scenario: Pedido pendente não estende a janela de outros itens

- **WHEN** a janela de 30 dias terminou e há um pedido pendente editável criado dentro dela, mas o carrinho também contém uma seleção anterior ao vencimento que ainda não pertence a esse pedido
- **THEN** a preparação ou atualização do checkout recusa a inclusão desse item e preserva o pedido e as seleções
- **AND** um carrinho composto somente pelos itens originais desse pedido pode retomá-lo, respeitando os demais gates; a regra vale para galerias canônicas e legadas

### Requirement: Pedido aberto com acesso elegível preserva prévia somente dos itens próprios

Depois da janela de 30 dias, um pedido criado até o fim dela SHALL manter prévias apenas dos próprios itens enquanto a pasta bloquear o arquivo, a mídia permanecer local e o pedido estiver em estado que permita acesso comercial: pendente e congelado após comunicação de pagamento, ou apto para entrega sem álbum de entrega definido. Um rascunho pendente editável bloqueia o arquivo, mas, sozinho, não prolonga o acesso às prévias além da janela.

#### Scenario: Pedido congelado não resolvido conserva acesso aos próprios itens

- **WHEN** a janela terminou, uma foto pertence a pedido elegível ainda não resolvido que está pendente e congelado após comunicação de pagamento, ou apto para entrega sem álbum definido, e a pasta continua local
- **THEN** a cliente pode abrir a prévia dessa foto pelo pedido, sem receber acesso à pasta ou a outras fotos

#### Scenario: Rascunho de checkout salvo bloqueia o arquivo

- **WHEN** a cliente preparou checkout até o fim da janela e existe um pedido pendente editável com itens vinculados à pasta, mesmo sem `frozen_at`
- **THEN** esse pedido continua sendo uma obrigação comercial em aberto: a descoberta e a conferência final bloqueiam o arquivo até pagamento comunicado, conclusão, cancelamento ou outra resolução válida; uma seleção/carrinho sem pedido salvo continua sem bloquear o arquivo
- **AND** os fluxos de criação de checkout editável SHALL serializar a persistência do pedido com o arquivamento usando locks das pastas selecionadas; se o arquivamento concluir primeiro, o checkout MUST falhar sem criar pedido que aponte para mídia fria

#### Scenario: Rascunho após a janela não prolonga prévias

- **WHEN** passaram 30 dias completos, existe somente um rascunho pendente editável criado dentro da janela e a cliente ainda não comunicou o pagamento
- **THEN** o pedido continua bloqueando o arquivo e pode seguir para comunicação de pagamento, mas não fornece `preview_url` nem permite prévia direta até alcançar um estado comercial elegível; depois do congelamento pelo pagamento comunicado, a prévia pode ser acessada somente para seus itens enquanto a mídia permanecer local

### Requirement: Carrinho sem pedido não prolonga disponibilidade da mídia

Um carrinho sem pedido SHALL NOT bloquear o arquivo. Depois da janela de 30 dias, suas referências permanecem registradas, mas as prévias deixam de ser servidas.

#### Scenario: Carrinho sem pedido permanece após o fim da janela

- **WHEN** os 30 dias terminam e existe somente seleção/carrinho, sem pedido aberto
- **THEN** a pasta fica elegível ao arquivo, a URL da prévia é ocultada e a requisição direta é rejeitada

#### Scenario: Mídia arquivada não fornece prévia

- **WHEN** a pasta está arquivada
- **THEN** nenhuma prévia da pasta é servida, ainda que uma seleção ou pedido mantenha referência à foto

### Requirement: Prazo próprio obrigatório em novas pastas

Cada nova pasta de conteúdo SHALL exigir um número inteiro positivo de dias escolhido pelo fotógrafo antes da liberação. O sistema SHALL NOT aplicar valor padrão ou herdar o prazo da galeria. A contagem SHALL começar em `released_at`; esse prazo controla acesso, reabertura e elegibilidade ao arquivo.

#### Scenario: Nova pasta exige prazo finito antes da liberação

- **WHEN** o fotógrafo tenta liberar uma nova pasta de conteúdo sem escolher número inteiro positivo de dias
- **THEN** o sistema bloqueia a liberação; não preenche prazo padrão nem herda a duração da galeria

#### Scenario: Contagem da nova pasta começa na liberação

- **WHEN** o fotógrafo libera uma pasta de conteúdo com prazo próprio válido
- **THEN** o sistema inicia a contagem em `released_at`, e a expiração é calculada com base nesse instante e no número de dias escolhido

#### Scenario: Duração excede a representação de datas

- **WHEN** criação, configuração, renovação ou aprovação de reabertura recebe uma duração cuja expiração acrescida da janela de 30 dias ultrapassa a representação de datas do sistema
- **THEN** a API recusa a entrada com 422 antes de gravar prazo, aprovação ou auditoria de sucesso, sem converter o valor em prazo padrão ou retornar erro interno

### Requirement: Pastas legadas começam sem prazo próprio

Pastas de conteúdo existentes quando essa mudança entrar em vigor SHALL iniciar sem prazo próprio e só entrar no ciclo após configuração explícita do proprietário. Ao configurar, a contagem SHALL começar no instante em que o proprietário salvar o prazo, sem expiração retroativa. O sistema SHALL preservar as seleções e os carrinhos existentes.

#### Scenario: Pasta legada ainda sem prazo

- **WHEN** uma pasta que já existia em produção no momento da mudança não recebeu prazo próprio
- **THEN** ela permanece com prazo indeterminado e não entra automaticamente no ciclo de arquivo até o proprietário configurar um prazo

#### Scenario: Prazo legado da galeria não é herdado

- **WHEN** uma pasta legada sem prazo próprio pertence a uma galeria com `selection_duration_days` configurado
- **THEN** o prazo da galeria não é copiado para a pasta e a pasta permanece indeterminada até configuração explícita do proprietário

#### Scenario: Prazo configurado em pasta legada

- **WHEN** o proprietário escolhe um prazo inteiro positivo para uma pasta legada sem prazo
- **THEN** a contagem começa no instante da configuração e não usa a data antiga de liberação para provocar expiração imediata ou retroativa

#### Scenario: Cliente consulta prazo de pasta

- **WHEN** a cliente visualiza uma pasta com prazo definido
- **THEN** vê o prazo daquela pasta, sem prazo herdado ou exibido como prazo de expiração da galeria

### Requirement: Orientação de arquivo aparece na criação da pasta

O formulário de criação de pasta SHALL mostrar uma única orientação curta sobre início do prazo e elegibilidade ao arquivo frio. Essa orientação MUST NOT ser repetida em cada card de pasta existente nem revelar ao fotógrafo o estado administrativo de configuração da taxa.

#### Scenario: Fotógrafo cria pasta com prazo

- **WHEN** o fotógrafo preenche o prazo de uma nova pasta
- **THEN** vê: “A contagem começa quando as fotos da pasta forem liberadas. Após a expiração, a pasta pode ir para o arquivo frio depois de 30 dias.”

#### Scenario: Fotógrafo configura prazo de pasta existente

- **WHEN** o fotógrafo define prazo para uma pasta legada
- **THEN** vê apenas quando a contagem começa após salvar, sem repetir o aviso de arquivo frio nem o estado interno de configuração da taxa

### Requirement: Taxa dinâmica é apresentada na criação da pasta

Quando a taxa global estiver configurada, o formulário de nova pasta SHALL mostrar o valor atual em créditos por pasta/ciclo e informar que o valor pode mudar antes de uma recuperação futura. Para a pasta do proprietário, SHALL mostrar a taxa de referência e a isenção de débito.

#### Scenario: Fotógrafo cria pasta com taxa configurada

- **WHEN** a taxa global está configurada e o fotógrafo cria uma pasta
- **THEN** o formulário apresenta o valor vigente sem incorporar um preço fixo ao código

#### Scenario: Proprietário cria pasta própria

- **WHEN** o proprietário cria uma pasta da própria conta
- **THEN** vê a taxa de referência e que não haverá débito de créditos na recuperação

### Requirement: Recuperação sem taxa configurada permanece bloqueada

Se não houver taxa global configurada no momento de uma solicitação paga de recuperação, o sistema MUST NOT reservar créditos nem iniciar o download. O fluxo isento do tenant do proprietário permanece disponível para ensaio.

#### Scenario: Tenant solicita recuperação sem taxa global

- **WHEN** um tenant sujeito a cobrança solicita recuperação e o proprietário ainda não definiu a taxa global
- **THEN** o sistema informa que a recuperação paga não está disponível, sem reservar créditos ou iniciar download

### Requirement: Termos operacionais divulgam a regra de arquivo e recuperação

Os Termos operacionais aceitos pelo fotógrafo SHALL explicar expiração por pasta, elegibilidade ao arquivo 30 dias depois, referências de seleção preservadas com fotos indisponíveis e recuperação pela taxa global vigente em créditos por pasta/ciclo. SHALL explicar que o valor é confirmado no pedido e debitado somente após pull bem-sucedido; falha não gera débito. O protocolo SHALL preservar essa versão e seu texto/hash pelo mecanismo de aceite existente.

#### Scenario: Tenant aceita os Termos operacionais

- **WHEN** o fotógrafo aceita a versão vigente dos Termos antes da primeira compra de créditos ou upload
- **THEN** o texto exibido inclui a regra de arquivo e recuperação e o protocolo registra a versão/texto/hash efetivamente aceitos

#### Scenario: Tenant consulta a regra de cobrança

- **WHEN** o tenant solicita recuperação de uma pasta
- **THEN** a interface apresenta a taxa global vigente e exige confirmação desse valor antes de reservar créditos e iniciar o pull

### Requirement: Reabertura normal limitada a 30 dias

O fluxo normal SHALL aceitar pedidos de reabertura somente nos 30 dias corridos após a expiração efetiva da pasta. Após essa janela, novos pedidos normais MUST ser recusados; mídia arquivada só pode voltar a ficar disponível pelo fluxo automatizado de recuperação definido nesta spec.

#### Scenario: Pedido normal após a janela

- **WHEN** a cliente solicita reabertura depois dos 30 dias corridos desde a expiração da pasta
- **THEN** o sistema recusa a reabertura normal e direciona o caso ao fluxo de recuperação fria

### Requirement: Renovação direta de pasta pública

O fotógrafo SHALL poder renovar uma pasta pública expirada diretamente no card, sem solicitação do cliente. SHALL informar dias inteiros positivos contados do salvamento; o prazo vale para todos os clientes já autorizados. O servidor MUST exigir tenant ativo, conta aberta, mídia disponível e janela de até 30 dias após o vencimento efetivo. Pastas privadas MUST manter o fluxo individual existente.

#### Scenario: Fotógrafo renova a pasta pública
- **WHEN** informa sete dias em pasta pública elegível e salva
- **THEN** todos os clientes já autorizados recebem sete dias a partir do salvamento, o contador usa o novo prazo e a elegibilidade ao arquivo passa para 30 dias após o novo vencimento, sem débito de créditos

#### Scenario: Confirmação do alcance
- **WHEN** o formulário de renovação é aberto
- **THEN** mostra “O novo prazo começa agora e vale para todos os clientes autorizados desta pasta.”

#### Scenario: Renovação indevida
- **WHEN** há chamada para outro tenant, pasta privada, prazo ainda vigente, janela vencida ou mídia indisponível
- **THEN** o backend recusa sem alterar prazo, autorizações, seleções, saldo ou histórico

#### Scenario: Escritas concorrentes
- **WHEN** duas renovações ou uma renovação e o arquivamento disputam a pasta
- **THEN** locks e revalidação impedem extensão dupla ou reabertura de mídia congelada; a ação aceita é auditada e avisos de prazo anterior são superados

### Requirement: Renovação preserva o prazo inicial

A renovação SHALL preservar a data original de liberação e o histórico de solicitações. MUST alterar somente o prazo base operacional e registrar auditoria no tenant. Requisições repetidas após o sucesso MUST NOT conceder uma segunda extensão enquanto o prazo estiver vigente.

#### Scenario: Repetição imediata
- **WHEN** o envio de renovação é repetido depois do primeiro sucesso
- **THEN** o prazo vigente permanece idêntico e não há segunda extensão

### Requirement: Público autorizado pela reabertura normal

Uma reabertura aprovada de pasta pública SHALL abranger todos os clientes já autorizados. A reabertura de pasta privada SHALL abranger somente a cliente solicitante.

#### Scenario: Reabertura de pasta pública

- **WHEN** o fotógrafo aprova, dentro da janela normal, um pedido de reabertura de uma pasta pública
- **THEN** todos os clientes já autorizados àquela pasta podem acessá-la pelo novo prazo

#### Scenario: Reabertura de pasta privada com vários clientes autorizados

- **WHEN** o fotógrafo aprova a reabertura de uma pasta privada para uma cliente solicitante
- **THEN** somente essa cliente recebe acesso; outras autorizações da pasta não são ampliadas

### Requirement: Prazo e cobrança da reabertura normal

O fotógrafo SHALL informar um número inteiro positivo de dias ao aprovar a reabertura. O prazo SHALL começar na aprovação e não gera taxa de recuperação fria.

#### Scenario: Duração da reabertura normal

- **WHEN** o fotógrafo aprova uma reabertura normal e informa um número inteiro positivo de dias
- **THEN** o novo prazo começa no instante da aprovação e não gera débito de créditos de recuperação

### Requirement: Integridade da pasta associada à reabertura

O banco e o ORM SHALL recusar a associação a uma pasta de outra galeria ou de outro tenant. Pedidos legados sem pasta SHALL permanecer preservados.

#### Scenario: Associação de pasta fora do escopo da reabertura

- **WHEN** uma escrita tenta associar ao pedido uma pasta de outra galeria ou de outro tenant
- **THEN** a transação é recusada por integridade referencial, inclusive no schema criado pelas migrations, sem persistir o pedido inválido

### Requirement: Elegibilidade física após reabertura privada

Uma pasta privada SHALL aguardar 30 dias completos após o prazo individual mais recente antes de ser elegível ao arquivo físico.

#### Scenario: Reabertura privada adia o arquivo físico

- **WHEN** uma cliente recebe prazo privado de reabertura em uma pasta com outras clientes autorizadas
- **THEN** somente ela tem acesso durante o prazo concedido, e o arquivo físico aguarda 30 dias completos após o prazo mais recente antes de ficar elegível

#### Scenario: Pedido de reabertura dentro da janela

- **WHEN** o cliente pede reabertura após a expiração da pasta e ainda dentro dos 30 dias
- **THEN** a solicitação segue o fluxo normal de decisão já existente

#### Scenario: Pedido de reabertura após a janela

- **WHEN** o cliente pede reabertura depois dos 30 dias corridos
- **THEN** o fluxo normal recusa a solicitação e mídia arquivada permanece indisponível até que o tenant conclua a recuperação paga em créditos

### Requirement: Verificar arquivo antes de liberar storage primário

O sistema SHALL transferir os objetos aprovados e persistir manifesto/checksum. Antes de remover qualquer cópia primária, SHALL ler cada objeto remoto em streaming e conferir tamanho e SHA-256 do manifesto.

#### Scenario: Transferência incompleta ou inválida

- **WHEN** upload, checksum ou leitura de prova falha
- **THEN** o sistema marca falha retomável, conserva os arquivos primários e registra a etapa sem perder referências

#### Scenario: Leitura de retorno confirma o objeto

- **WHEN** o sistema lê integralmente cada objeto remoto pelo ID registrado
- **THEN** só confirma o ciclo e libera storage primário se tamanho e SHA-256 coincidirem com o manifesto

#### Scenario: Cleanup não deixa a pasta parcialmente visível

- **WHEN** todos os objetos e o manifesto foram relidos e verificados
- **THEN** o sistema muda o ciclo para `archived` antes de remover qualquer arquivo local, mantendo toda a pasta invisível durante o cleanup retomável

#### Scenario: Gravação concorrente impede o snapshot

- **WHEN** o ciclo começa a arquivar enquanto há upload ou geração de mídia pendente na pasta
- **THEN** o sistema bloqueia novas gravações, espera trabalhos pendentes terminarem e só então congela o conjunto de objetos do manifesto

### Requirement: Manifesto versionado descreve o ciclo de arquivo

Cada ciclo SHALL ter manifesto versionado (`schema_version`) com IDs tenant-scoped, timestamp UTC, objetos, contagem e bytes totais. Cada objeto SHALL conter UUID opaco, `source_ref` validado, tipo permitido, MIME type, tamanho, SHA-256 e ID remoto. O sistema MUST validar totais e hash canônico. PII, caminhos locais absolutos, credenciais e URLs SHALL NOT constar no manifesto.

#### Scenario: Totais do manifesto correspondem aos objetos

- **WHEN** o sistema prepara o manifesto a partir dos objetos autorizados do ciclo
- **THEN** ordena entradas por UUID, calcula contagem/bytes e associa o hash SHA-256 canônico à operação

#### Scenario: Retry comprovado preserva a identidade imutável do manifesto

- **WHEN** uma nova operação tenta concluir o mesmo ciclo após falha comprovada que preservou o snapshot e o manifesto
- **THEN** o sistema mantém `operation_id`, `created_at`, IDs remotos e checksums originais, relê objetos já confirmados sem reenviá-los e só prossegue se a reconstrução canônica for idêntica

#### Scenario: Manifesto aponta objeto de outro escopo

- **WHEN** uma entrada não pertence ao tenant, galeria, pasta ou ciclo registrado localmente
- **THEN** o sistema recusa o manifesto e não inicia transferência nem remoção primária

#### Scenario: Serialização do manifesto é canônica

- **WHEN** o sistema gera o manifesto ou recalcula seu hash
- **THEN** usa JSON UTF-8 com chaves ordenadas, entradas ordenadas por UUID, separadores compactos, sem floats, chaves duplicadas ou campos desconhecidos

### Requirement: Cópia global preserva catálogo frio sem duplicar a mídia

A cópia global do PostgreSQL SHALL preservar o catálogo, estados de operação, manifesto e IDs/checksums remotos, mantendo os bytes de mídia na identidade e raiz fria separadas. Restaurar o banco MUST NOT tornar mídia fria visível sem reconciliação do catálogo remoto e sem o fluxo normal de recuperação.

#### Scenario: Banco global restaurado com referência fria

- **WHEN** o catálogo de arquivo frio é restaurado sem os bytes de mídia
- **THEN** o sistema reconcilia IDs e checksums com a raiz fria e mantém indisponível qualquer objeto ausente, divergente ou ainda não recuperado

### Requirement: Staging local é segregado por tenant e operação

O sistema SHALL usar área temporária privada no servidor, segregada por UUID de tenant e de operação, sem expô-la por rotas ou servir caminhos fornecidos pelo cliente. O pré-flight de recuperação SHALL contabilizar espaço por volume, incluindo reservas de operações concorrentes.

#### Scenario: Dois tenants restauram no mesmo servidor

- **WHEN** dois tenants têm operações de recuperação no mesmo período
- **THEN** cada operação usa staging distinto e o backend confere ownership antes de resolver caminhos ou objetos

#### Scenario: Reservas concorrentes excedem capacidade disponível

- **WHEN** o espaço livre de um volume, descontadas as reservas de outros pulls ativos, não comporta o próximo pacote e a margem aprovada
- **THEN** o sistema não inicia o download nem reserva créditos para esse pedido

### Requirement: Pré-flight preserva espaço mínimo em cada volume

Antes de iniciar uma recuperação, o sistema SHALL confirmar em cada volume afetado espaço para todas as cópias que coexistem durante staging e promoção, além de uma reserva mínima após a operação, igual ao maior valor entre 10 GiB e 15% da capacidade total do volume. Quando staging e destino compartilharem volume, os bytes das duas cópias SHALL ser somados. Reservas ativas de outros pulls SHALL ser descontadas.

#### Scenario: Pré-flight não encontra espaço suficiente

- **WHEN** algum volume não comporta o pacote e a reserva mínima
- **THEN** o sistema não baixa bytes, não reserva créditos e avisa o tenant para tentar depois

#### Scenario: Preflight concorrente reserva capacidade

- **WHEN** duas operações avaliam simultaneamente o mesmo volume
- **THEN** o sistema serializa ou reserva a capacidade atomicamente para que a segunda avaliação considere o espaço já comprometido

### Requirement: Fila limita transferência e prioriza recuperação

A fila SHALL permitir no máximo uma transferência fria global ativa por vez. Recuperações solicitadas por tenant ou proprietário SHALL ter prioridade sobre novos arquivamentos; dentro de cada classe a fila SHALL respeitar a ordem de criação. O bloqueio global SHALL persistir e funcionar entre réplicas.

#### Scenario: Recuperação e arquivamento aguardam

- **WHEN** existe uma recuperação na fila e um novo arquivo frio também está elegível
- **THEN** o sistema executa a recuperação primeiro e mantém o arquivo frio aguardando

#### Scenario: Segunda réplica tenta reivindicar transferência

- **WHEN** uma instância já possui o lease global da transferência
- **THEN** outra instância não inicia um segundo upload ou pull e mantém o job na fila

#### Scenario: Lease expirado retoma o mesmo job idempotente

- **WHEN** o lease de um job em andamento expira e o último checkpoint identifica uma etapa idempotente
- **THEN** o worker reivindica o mesmo job e continua pelo checkpoint, sem criar outra operação para o ciclo

#### Scenario: Resultado externo incerto exige reconciliação

- **WHEN** o worker não consegue confirmar se um efeito externo foi concluído
- **THEN** marca a operação para reconciliação, conserva a mídia primária e as reservas ainda necessárias, e não repete automaticamente o efeito

### Requirement: Pacote de arquivo respeita escopo aprovado

O pacote SHALL incluir JPEGs originais, capas, prévias/derivados e mídia associada a compras; MUST excluir dados biométricos. Pedidos e pagamentos SHALL permanecer no banco, sem duplicação ou remoção pelo arquivo.

#### Scenario: Pacote de pasta preparado

- **WHEN** o sistema prepara o pacote de uma pasta elegível
- **THEN** inclui os arquivos de imagem e mídia de compra aprovados, omite referências faciais, embeddings e dados de busca biométrica, e preserva pedidos e pagamentos no banco

### Requirement: Ativos e miniatura de capa acompanham a última pasta ativa

O sistema SHALL manter os ativos da pasta técnica `cover_assets` e a miniatura de uma foto `content` selecionada como capa enquanto existir qualquer pasta de conteúdo ativa na galeria. Quando a última pasta de conteúdo for arquivada, esses ativos SHALL acompanhar esse mesmo ciclo, sem criar um ciclo de acesso separado.

#### Scenario: Galeria ainda tem pasta ativa

- **WHEN** uma pasta de conteúdo é arquivada, mas outra pasta de conteúdo da mesma galeria continua ativa
- **THEN** os ativos técnicos de capa permanecem no servidor e disponíveis conforme as permissões atuais da galeria

#### Scenario: Foto de capa vem de pasta arquivada

- **WHEN** a pasta de origem da foto escolhida como capa é arquivada e outra pasta da galeria continua ativa
- **THEN** somente a miniatura reduzida usada como capa permanece no servidor; o original e os demais derivados seguem para o arquivo da pasta de origem

#### Scenario: Última pasta de conteúdo é arquivada

- **WHEN** a última pasta de conteúdo da galeria é arquivada após cumprir as regras de elegibilidade
- **THEN** os ativos `cover_assets` e a miniatura de capa preservada acompanham o manifesto desse ciclo e não são transferidos como um ciclo de recuperação separado

#### Scenario: Ativo compartilhado de capa está arquivado

- **WHEN** os ativos técnicos ou a miniatura compartilhada da capa já foram arquivados com a última pasta de conteúdo
- **THEN** novas gravações nesses ativos e a seleção de uma foto arquivada como capa são recusadas até a recuperação íntegra do ciclo correspondente

#### Scenario: Capa compartilhada acompanha ciclos de pastas diferentes

- **WHEN** o mesmo ativo de capa aparece em ciclos de pastas diferentes da galeria
- **THEN** sua disponibilidade é determinada pelo ciclo criado mais recentemente que contém esse ativo, com desempate determinístico pelo identificador do ciclo
- **AND** o número do ciclo, que é local a cada pasta, não faz um ciclo antigo prevalecer sobre o estado mais recente de outra pasta

### Requirement: Pedidos em aberto bloqueiam o arquivamento, mas seleções não

O sistema MUST bloquear o início do arquivo enquanto qualquer pedido da pasta aguardar pagamento, produção/edição ou entrega. A elegibilidade comercial só é liberada quando todos os pedidos estiverem concluídos, cancelados ou reembolsados. Carrinhos e seleções em aberto MUST NOT bloquear o arquivo; suas referências SHALL permanecer preservadas.

#### Scenario: Há pedido em aberto

- **WHEN** a janela de reabertura terminou, mas existe pedido aguardando pagamento, produção/edição ou entrega
- **THEN** o sistema não transfere nem remove a mídia primária da pasta

#### Scenario: Há somente seleção ou carrinho em aberto

- **WHEN** a janela de reabertura terminou, não há pedidos em aberto e existem fotos selecionadas em um ou mais carrinhos
- **THEN** as referências dos itens selecionados permanecem registradas, mas não impedem a transferência e o arquivo das imagens

### Requirement: Arquivo frio oculta mídia e preserva seleção

Enquanto uma pasta estiver arquivada, o cliente SHALL NOT visualizar nem selecionar suas imagens ou derivados, exceto a miniatura reduzida mantida exclusivamente como capa enquanto outra pasta da galeria estiver ativa. O sistema SHALL preservar os registros e referências dos itens já selecionados.

#### Scenario: Cliente consulta seleção com mídia arquivada

- **WHEN** o cliente abre uma seleção que referencia fotos arquivadas
- **THEN** os itens e seu estado continuam registrados, as imagens não são exibidas como itens selecionáveis e o sistema informa que a mídia está indisponível até a recuperação

#### Scenario: Cliente retoma seleção após recuperação

- **WHEN** a recuperação da pasta termina e os arquivos são verificados no servidor
- **THEN** a mídia volta a ficar visível conforme as permissões da pasta e o cliente pode continuar a seleção ou finalizar a compra

### Requirement: Recuperação automática por créditos após pedido do tenant

O sistema SHALL permitir a recuperação automática de pastas arquivadas por solicitação do tenant, aplicando a taxa global e um dos prazos permitidos.

#### Scenario: Tenant solicita recuperação com saldo e espaço suficientes

- **WHEN** o tenant confirma a recuperação, possui saldo suficiente para a taxa global vigente e o pré-flight de espaço passa
- **THEN** o tenant vê a taxa, o prazo escolhido e o aviso de possível nova taxa em outro ciclo; o sistema reserva temporariamente os créditos e inicia automaticamente o pull do Drive para o servidor sem aprovação manual do proprietário

#### Scenario: Tenant solicita recuperação sem saldo suficiente

- **WHEN** o saldo de créditos disponível não cobre a taxa configurada
- **THEN** o sistema não inicia o pull e informa que é necessário adquirir créditos para recuperar a pasta

#### Scenario: Tenant escolhe prazo de recuperação

- **WHEN** o tenant confirma uma das opções de 7, 14 ou 30 dias
- **THEN** o sistema registra a opção e aplica a mesma taxa fixa por pasta/ciclo para todas as opções; o prazo começa somente após a recuperação íntegra

#### Scenario: Prazo de recuperação fora das opções

- **WHEN** uma chamada envia duração diferente de 7, 14 ou 30 dias
- **THEN** o sistema rejeita a solicitação antes de reservar créditos ou iniciar o pull

#### Scenario: Proprietário configura a taxa global

- **WHEN** o proprietário altera a taxa de recuperação na página Créditos
- **THEN** o novo valor fixo em créditos por pasta e ciclo vale para novos pedidos de todos os tenants

#### Scenario: Taxa configurada vale para todos os prazos

- **WHEN** tenants escolhem prazos de recuperação diferentes
- **THEN** cada pedido aplica a mesma taxa global fixa por pasta e ciclo

#### Scenario: Proprietário segue o fluxo de recuperação

- **WHEN** o proprietário solicita recuperação para acompanhar o mesmo fluxo usado pelos tenants
- **THEN** o sistema aplica as mesmas etapas e verificações, registra a operação e isenta o proprietário do débito e da reserva de créditos

#### Scenario: Pedido chega enquanto já existe recuperação ativa

- **WHEN** um segundo pedido chega para um ciclo cuja recuperação ainda está ativa
- **THEN** a API recusa sem criar outra operação ou reserva, e o worker pode concluir a operação existente

### Requirement: Taxa de recuperação aparece ao configurar o prazo da pasta

Os formulários que definem o prazo de acesso da pasta SHALL consultar e exibir a taxa global vigente por pasta e ciclo, explicando que os créditos ficam reservados e só são debitados após a recuperação completa e verificada. A carteira do proprietário SHALL ser identificada como isenta. O formulário MUST NOT embutir um valor fixo; se a taxa não estiver configurada ou não puder ser consultada, SHALL informar que o valor está indisponível sem apresentar um preço incorreto.

#### Scenario: Fotógrafo consulta formulário com taxa configurada

- **WHEN** o fotógrafo abre o formulário de prazo e a taxa global está configurada
- **THEN** o formulário mostra o número atual de créditos por pasta/ciclo e o momento em que a cobrança ocorre

#### Scenario: Proprietário consulta formulário de prazo

- **WHEN** o proprietário abre o formulário para uma pasta de sua própria conta
- **THEN** o formulário informa a isenção de créditos e não apresenta a taxa como cobrança para essa conta

#### Scenario: Taxa não configurada ou indisponível

- **WHEN** o formulário não consegue obter um preço configurado e vigente
- **THEN** informa que a recuperação paga ainda não pode ser precificada e não inventa um valor

### Requirement: Débito da recuperação ocorre somente após pull completo e verificado

O sistema SHALL usar o ledger de créditos para registrar o consumo de recuperação, com tenant, pasta, ciclo, taxa aplicada e resultado auditável. O valor e a versão da taxa SHALL ser congelados no início da operação. O débito SHALL ocorrer somente depois que todos os objetos esperados forem puxados e passarem pela verificação de integridade. Falha comprovada MUST NOT debitar e SHALL liberar a reserva; resultado indeterminado MUST NOT debitar e SHALL manter reserva em reconciliação até resolução.

#### Scenario: Pull completo e íntegro

- **WHEN** todos os arquivos esperados são puxados e passam na verificação de integridade
- **THEN** o sistema promove os objetos locais ainda invisíveis e, na transação final, confirma uma única vez o débito reservado, registra o histórico e ativa a pasta e o prazo escolhido

#### Scenario: Pull falha ou fica incompleto

- **WHEN** algum objeto não é puxado ou falha na verificação de integridade
- **THEN** o sistema não debita créditos, libera a reserva, mantém o estado de falha retomável e conserva as referências da seleção

#### Scenario: Promoção local ou finalização é interrompida

- **WHEN** todos os objetos foram verificados, mas uma promoção local ou a transação final de ativação é interrompida
- **THEN** a pasta permanece invisível em `restoring`, sem débito duplicado, e a operação retoma ou reconcilia usando a reserva existente

#### Scenario: Resultado do pull é indeterminado

- **WHEN** o sistema não consegue provar se todos os objetos foram restaurados de forma íntegra
- **THEN** não debita créditos, marca reconciliação necessária, conserva temporariamente a reserva e bloqueia novo consumo até o proprietário resolver o estado

#### Scenario: A taxa muda durante uma recuperação

- **WHEN** o proprietário altera a taxa global depois do início de uma recuperação
- **THEN** a operação em andamento mantém o valor congelado no pedido e a nova taxa vale para novos pedidos

### Requirement: Avisos de arquivo são internos e direcionados ao fotógrafo

O sistema SHALL disponibilizar os avisos de arquivo frio em caixa autenticada do fotógrafo responsável. Nesta versão, SHALL NOT criar entrega externa de push, WhatsApp ou e-mail, lembretes diários ou mensagens novas ao cliente por causa do arquivo frio.

#### Scenario: Fotógrafo consulta os avisos

- **WHEN** o fotógrafo abre a caixa autenticada de avisos
- **THEN** consulta apenas os avisos do próprio tenant e pode marcar cada aviso como lido

### Requirement: O aviso de prazo acompanha a reabertura mais recente

O sistema SHALL emitir uma vez o aviso de prazo sete dias antes da elegibilidade física, calculada pela expiração efetiva e pela janela de 30 dias. Nova aprovação que altere o prazo SHALL superar o aviso anterior e permitir um único aviso para o novo marco.

#### Scenario: Reabertura altera o prazo avisado

- **WHEN** uma reabertura aprovada altera a elegibilidade de uma pasta
- **THEN** o aviso anterior fica identificado como superado e um único aviso pode surgir sete dias antes da nova elegibilidade

### Requirement: O andamento da transferência gera avisos idempotentes

O sistema SHALL avisar uma vez por ciclo quando pedido em aberto bloquear o arquivo e quando transferência de arquivo ou recuperação iniciar, concluir, falhar ou exigir reconciliação. O aviso SHALL omitir erros brutos, caminhos e segredos.

#### Scenario: Pedido ou transferência muda o estado do ciclo

- **WHEN** um pedido bloqueia o ciclo ou uma transferência altera seu estado
- **THEN** o fotógrafo consulta um aviso interno correspondente sem entrega externa ao cliente

### Requirement: Recuperação renova prazo e permite novo ciclo

Após a recuperação, a pasta SHALL ficar disponível pelo prazo escolhido pelo tenant. Ao fim desse prazo começa uma nova janela de 30 dias corridos completos; se os pedidos não estiverem em aberto, a pasta torna-se elegível para novo ciclo de arquivo e uma recuperação posterior exige nova taxa por ciclo. O proprietário segue a mesma regra de prazo sem pagar.

#### Scenario: Novo prazo termina

- **WHEN** o prazo escolhido termina e passam 30 dias corridos completos sem pedido em aberto
- **THEN** a pasta torna-se elegível a ser arquivada novamente, sem bloqueio por carrinhos/seleções, e uma nova recuperação segue a taxa vigente daquele ciclo

### Requirement: Operação de recuperação fica visível no card e no histórico do tenant

O sistema SHALL registrar por pasta cada solicitação, estado, prazo escolhido, taxa, reserva, débito/liberação e resultado no card do tenant e no histórico de créditos. O proprietário SHALL poder consultar o estado e iniciar retry manual somente após falha, com auditoria. Detalhes técnicos SHALL ser sanitizados e MUST NOT revelar segredos, URLs assinadas, imagens ou PII desnecessária.

#### Scenario: Tenant acompanha a recuperação

- **WHEN** uma recuperação é solicitada, processada, concluída ou falha
- **THEN** o card do tenant e seu histórico exibem a pasta, prazo, estado e movimentação de créditos correspondente sem duplicar consumo

#### Scenario: Proprietário faz retry após falha

- **WHEN** uma recuperação automática falha e o proprietário inicia retry para o tenant
- **THEN** o sistema registra o PlatformOwner como ator e vincula a nova operação à falha anterior, exige saldo suficiente e reserva exatamente a taxa congelada no pedido que falhou, preserva a idempotência do ciclo e só debita se o pull terminar completo e verificado

#### Scenario: Saldo insuficiente para retry manual

- **WHEN** o proprietário inicia retry, mas o tenant não possui saldo disponível para a taxa congelada no pedido original
- **THEN** o pull não inicia, a interface informa que o tenant precisa adquirir créditos e nenhum débito é criado

#### Scenario: Retry manual termina sem sucesso

- **WHEN** o retry manual do proprietário falha antes de concluir e verificar o pull
- **THEN** a reserva é liberada, nenhum crédito é debitado e o erro sanitizado fica visível ao proprietário

#### Scenario: Proprietário consulta erro

- **WHEN** o proprietário abre os detalhes de uma recuperação com falha
- **THEN** vê categoria, etapa, horário e identificador de correlação suficientes para diagnóstico, sem segredos, URLs assinadas, imagens ou PII desnecessária

### Requirement: Histórico informa estado da mídia

O histórico comercial SHALL continuar consultável durante o arquivo e indicar mídia arquivada, restaurando, indisponível ou restaurada sem apresentar o item como inexistente. A movimentação de créditos por recuperação SHALL aparecer no histórico do tenant sem duplicar pedidos ou pagamentos. As interfaces e APIs SHALL preservar nomes, IDs, carrinho, seleção e pedidos existentes enquanto ocultam previews, downloads e URLs remotas quando os bytes não estiverem locais.

#### Scenario: Pasta removida fora do arquivo frio conserva mídia histórica local

- **WHEN** o item autorizado conserva o UUID da pasta no snapshot, a pasta operacional já foi removida fora do arquivo frio e sua mídia histórica permanece pronta e local
- **THEN** listagem, prévia, entrega e HTML preservam o acesso histórico da própria cliente e tenant, sem exigir recriação da pasta
- **AND** um ciclo frio vigente continua bloqueando exposição dos bytes enquanto sua recuperação não estiver concluída

#### Scenario: Compra ou seleção vinculada a mídia arquivada

- **WHEN** fotógrafo ou cliente consulta um pedido ou seleção cuja mídia não está no storage primário
- **THEN** a interface mantém os registros, informa o estado da mídia, preserva as referências dos itens selecionados e não expõe link público nem conteúdo de outro tenant

### Requirement: Interfaces preservam referências e mostram o estado da mídia

O sistema SHALL exibir ao fotógrafo e ao cliente o estado de cada pasta indisponível. Nomes, IDs, carrinho, seleção e pedidos SHALL permanecer visíveis sem apresentar as fotos como inexistentes.

#### Scenario: Cliente abre pasta arquivada ou em recuperação

- **WHEN** o cliente consulta sua galeria, carrinho ou histórico enquanto os bytes da pasta estão no arquivo frio ou retornando em staging
- **THEN** o sistema preserva os nomes, IDs e referências selecionadas, informa `arquivada` ou `recuperação em andamento` e não mostra previews nem oferece links para esses bytes

#### Scenario: Fotógrafo consulta sua pasta arquivada

- **WHEN** o fotógrafo abre a administração da pasta arquivada, em recuperação ou em reconciliação
- **THEN** a interface exibe o estado, não cria links de preview e bloqueia upload, edição e exclusão de mídia até o ciclo terminar

#### Scenario: Pull íntegro torna a mídia local

- **WHEN** o pull completo é verificado e a transação final retorna a pasta ao estado `local`
- **THEN** os mesmos registros, IDs de foto, seleção e itens do histórico voltam a apresentar as prévias locais, sem duplicar entidades comerciais

### Requirement: Listagens e endpoints protegem bytes não locais

APIs SHALL omitir links de conteúdo, e endpoints protegidos SHALL negar bytes quando a mídia estiver `archived`, `restoring`, `reconciliation_required`, `deleting` ou `deleted`.

#### Scenario: Cliente tenta abrir foto arquivada ou em recuperação

- **WHEN** o cliente consulta links ou solicita preview/entrega enquanto a pasta não está local
- **THEN** a listagem não apresenta o link e o endpoint não devolve os bytes

#### Scenario: Administração consulta pasta em transferência ou reconciliação

- **WHEN** o fotógrafo consulta upload, edição e exclusão de uma pasta em estado diferente de `available`
- **THEN** a interface bloqueia essas ações e não oferece link de preview remoto

### Requirement: Previews seguem a disponibilidade local

Durante `archiving`, previews SHALL ficar disponíveis apenas enquanto os bytes íntegros permanecerem locais. A miniatura de capa retida no servidor segue a regra própria da última pasta ativa.

#### Scenario: Arquivo em andamento ou capa retida

- **WHEN** o ciclo está em `archiving` com origem local, ou a capa permanece retida enquanto outra pasta está ativa
- **THEN** somente a mídia ainda local permitida pelas regras de capa pode ser exibida; nenhuma URL do Drive é usada como preview

### Requirement: Arquivos frios não são expurgados automaticamente na primeira versão

Na primeira versão, o sistema MUST NOT apagar automaticamente cópias frias com base na idade do arquivo ou no encerramento da conta do tenant. Esta regra não define prazo legal de retenção nem implementa exclusão por solicitação; esses fluxos exigem política e change próprias.

#### Scenario: Cópia fria envelhece ou a conta é encerrada

- **WHEN** uma cópia fria ultrapassa qualquer idade ou o tenant encerra sua conta
- **THEN** o sistema não expurga automaticamente a cópia do Drive nesta versão

### Requirement: Inventário agregado preserva registros do arquivo

O inventário de manutenção SHALL reconhecer explicitamente as tabelas de arquivo, recuperação, encerramento e versões dos Termos como preservadas, retornando somente contagens. A limpeza integral legada MUST NOT remover histórico de arquivo ou encerramento, nem operar com schema desconhecido.

#### Scenario: Consulta com schema SaaS conhecido
- **WHEN** o operador consulta somente o inventário com as tabelas SaaS conhecidas
- **THEN** recebe contagens agregadas sem dados pessoais ou identificadores e nenhum registro é alterado

#### Scenario: Limpeza legada encontra histórico protegido
- **WHEN** uma execução de limpeza integral de homologação encontra histórico de arquivo ou encerramento
- **THEN** recusa a exclusão antes de acessar ou remover mídia; a conferência é serializada com inserções nessas fontes
