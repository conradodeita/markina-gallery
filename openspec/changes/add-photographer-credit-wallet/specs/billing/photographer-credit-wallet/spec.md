# billing/photographer-credit-wallet Specification

## ADDED Requirements

### Requirement: Carteira pré-paga por tenant

O sistema SHALL manter créditos pré-pagos associados ao tenant comprador, sem expiração. Créditos, pagamentos e pontos de fidelidade SHALL permanecer em estruturas contábeis separadas. O saldo SHALL derivar do ledger ou de uma projeção reconstruível.

#### Scenario: Fotógrafo consulta carteira

- **WHEN** um fotógrafo autenticado abre sua carteira
- **THEN** o servidor apresenta somente o saldo e os movimentos do tenant derivado da sessão, incluindo data, quantidade, origem e descrição

#### Scenario: Acesso cruzado

- **WHEN** uma chamada tenta ler ou alterar carteira ou movimento de outro tenant
- **THEN** o servidor recusa sem revelar saldo ou atividade financeira alheia

### Requirement: Ledger imutável e alocação FIFO por origem

Cada crédito positivo SHALL permanecer rastreável à sua origem por eventos de alocação imutáveis. Reservas e consumos SHALL alocar primeiro o crédito disponível mais antigo por `(created_at, id)`. Operações normais MUST NOT editar saldo arbitrariamente nem apagar movimentos ou alocações confirmadas.

#### Scenario: Auditoria e correção

- **WHEN** uma correção, estorno ou reconciliação financeira é necessária
- **THEN** ela gera evento próprio com origem, referência, data, estado e chave idempotente; nenhum movimento confirmado é apagado ou editado

### Requirement: Tenant do proprietário sem limite

O tenant explicitamente associado à conta permanente do proprietário global SHALL permanecer ilimitado e sem débito por upload. Essa exceção MUST NOT ser atribuída a outros tenants por e-mail ou permissão técnica.

#### Scenario: Conta do proprietário sem limite

- **WHEN** o proprietário envia conteúdo pelo tenant associado explicitamente à sua conta permanente
- **THEN** o sistema não reserva nem debita créditos e apresenta a carteira como ilimitada; outros tenants continuam sujeitos à carteira finita

### Requirement: Pacotes globais configuráveis

Somente o proprietário global identificado pela conta permanente SHALL conseguir administrar pacotes com nome, quantidade de créditos, preço, estado ativo/inativo e informações para checkout, conceder créditos e revogar concessões. O sistema SHALL iniciar sem preços ou quantidades comerciais presumidos. A administração SHALL exigir autorização comercial global explícita, auditável e independente da sessão de fotógrafo e da permissão técnica de diagnóstico da instalação.

#### Scenario: Pacote indisponível

- **WHEN** um pacote está inativo ou não configurado
- **THEN** ele não é oferecido nem pode ser comprado

#### Scenario: Administrador sem permissão comercial

- **WHEN** fotógrafo ou operador apenas técnico tenta administrar pacotes
- **THEN** a ação é recusada e auditada sem expor credenciais ou alterar configuração

#### Scenario: Proprietário administra carteira de fotógrafo

- **WHEN** o proprietário global abre a gestão de créditos
- **THEN** o sistema lista e permite selecionar tenants, apresenta seu saldo, estado e histórico recente, e permite conceder créditos ou escolher uma concessão ainda disponível para revogação parcial ou total
- **AND** cada concessão ou revogação exige quantidade e referência explícitas, é idempotente e gera movimento de ledger e evento de auditoria
- **AND** o tenant ilimitado do proprietário aparece como ilimitado e não aceita concessão ou revogação de créditos

#### Scenario: Revogação parcial de concessão

- **WHEN** o proprietário revoga parte de uma concessão de créditos
- **THEN** o servidor identifica o grant de origem, considera alocações consumidas e reservas FIFO, e registra uma entrada negativa e evento de alocação somente até o restante livre daquele grant

#### Scenario: Revogação excede o lote não utilizado

- **WHEN** a quantidade solicitada excede os créditos livres da concessão escolhida
- **THEN** a operação é recusada sem alterar ledger, saldo, reservas ou alocações

### Requirement: Reserva de crédito antes do upload

Para tenants com carteira finita, o sistema SHALL verificar o saldo e reservar um crédito por novo JPEG de conteúdo (`PhotoFolder.purpose = content`) antes de aceitar os bytes. Capas técnicas (`cover_assets`) SHALL NOT consumir créditos. O tenant associado ao proprietário SHALL usar a exceção ilimitada do requisito de carteira. Falha técnica comprovada antes de armazenamento durável SHALL liberar a reserva.

#### Scenario: Lote parcialmente concluído

- **WHEN** alguns JPEGs do lote são armazenados e outros falham tecnicamente
- **THEN** somente operações de fotos concluídas consomem crédito; reservas de falhas comprovadas são liberadas e o estado de cada item pode ser retomado

#### Scenario: Upload de capa técnica

- **WHEN** o fotógrafo envia um JPEG para uma pasta `cover_assets`
- **THEN** o sistema prepara e processa a capa sem reservar nem debitar crédito

### Requirement: Consumo idempotente por operação lógica

O sistema SHALL confirmar um crédito somente uma vez quando um novo JPEG de conteúdo da operação lógica estiver efetivamente armazenado. Retry, repetição HTTP, reindex facial do mesmo `PhotoAsset` e retry automático MUST NOT gerar um segundo consumo. Uma operação deliberadamente nova MUST possuir identidade própria, distinta da operação repetida.

#### Scenario: Replay e chamada concorrente

- **WHEN** a mesma operação é reenviada após timeout ou recebida concorrentemente
- **THEN** todas as chamadas convergem a uma única reserva/consumo idempotente sem saldo negativo ou débito duplicado

#### Scenario: Reindex facial da mesma foto

- **WHEN** uma fonte já cobrada é reprocessada com `x-facial-reindex: true`
- **THEN** o processamento reutiliza a operação de crédito do mesmo `PhotoAsset` e não cria outro débito

#### Scenario: Novo envio deliberado de bytes idênticos

- **WHEN** o fotógrafo seleciona novamente de forma deliberada um JPEG cujos bytes já foram enviados à mesma pasta
- **THEN** o sistema identifica uma nova intenção de upload, cria um `PhotoAsset` e uma operação de crédito próprios, e consome mais um crédito após a nova fonte ficar durável
- **AND** retry HTTP, retomada do mesmo lote/operação e reindex facial preservam a identidade da intenção original e não geram segundo débito

#### Scenario: Confirmação antes de enviar fotos repetidas

- **WHEN** a seleção contém bytes JPEG que já existem na pasta
- **THEN** o sistema apresenta um aviso antes de registrar ou transferir os arquivos repetidos, informa a quantidade e esclarece o possível consumo de créditos
- **AND** se o fotógrafo confirmar, envia as repetidas como novas intenções, com uma unidade por foto concluída
- **AND** se o fotógrafo cancelar, pula somente as repetidas e continua enviando as fotos ainda ausentes da pasta
- **AND** o servidor exige a confirmação explícita para registrar fingerprint já presente, inclusive quando outra sessão inseriu a foto após a consulta prévia

### Requirement: Consistência de saldo em lote e concorrência

Em lote parcial, o sistema SHALL consumir créditos somente pelas fotografias armazenadas com sucesso. Operações concorrentes MUST NOT produzir saldo inconsistente.

#### Scenario: Falha após gravação durável

- **WHEN** a fonte foi publicada no storage, mas a confirmação transacional ou a resposta HTTP falha
- **THEN** a recuperação reconcilia a mesma operação por identidade e fingerprint, preserva o arquivo e confirma exatamente um consumo, sem criar débito duplicado; se não conseguir verificar o arquivo, mantém a operação pendente de reconciliação sem apagar a fonte nem liberar saldo prematuramente

#### Scenario: Consulta anterior não substitui o estado da nova tentativa

- **WHEN** uma nova tentativa de upload começa para uma foto enquanto uma consulta do estado de créditos da tentativa anterior ainda está em andamento
- **THEN** a resposta atrasada não substitui o estado `uploading` nem a carteira da tentativa atual; a interface aguarda a confirmação correspondente à tentativa atual

#### Scenario: Reconciliação concorrente termina sem bloquear a carteira

- **WHEN** um upload e o reconciliador disputam a mesma operação de crédito do tenant
- **THEN** as chamadas serializam pela carteira do tenant, convergem ao mesmo estado idempotente e não criam débito duplicado; uma fonte de estado desconhecido mantém a reserva pendente

### Requirement: Histórico de créditos e reversões

O painel do fotógrafo SHALL apresentar saldo atual, créditos adquiridos, usados, concedidos por fidelidade e estornados, além do histórico com data, quantidade, origem e descrição. Créditos comprados e concedidos por fidelidade SHALL não expirar. Reembolso, estorno, chargeback e eventual restituição por política autorizada SHALL gerar eventos próprios e relações auditáveis, sem misturar ledger de crédito, pagamento e fidelidade.

#### Scenario: Exclusão manual de foto

- **WHEN** o fotógrafo exclui manualmente uma fotografia cujo upload já consumiu crédito
- **THEN** o sistema não devolve crédito automaticamente, salvo política específica previamente configurada e autorizada pelo proprietário

#### Scenario: Proibição de confisco

- **WHEN** uma política comercial propõe debitar créditos já consumidos ou confiscar saldo
- **THEN** o sistema não aplica a política sem decisão explícita e auditável do proprietário

### Requirement: Resumo financeiro no dashboard do fotógrafo

O dashboard do fotógrafo SHALL apresentar saldo disponível, consumo recente de créditos e operações de upload pendentes junto ao resumo operacional existente. Avisos de saldo insuficiente SHALL refletir resposta autoritativa do servidor para a conta e operação do tenant autenticado. A indisponibilidade da carteira MUST NOT ser apresentada como saldo zero nem ocultar os dados operacionais carregados.

#### Scenario: Dashboard apresenta saldo e consumo recentes

- **WHEN** o fotógrafo autenticado abre o dashboard e a consulta da carteira está disponível
- **THEN** o painel apresenta saldo disponível, movimentações recentes e operações de upload pendentes do tenant da sessão, junto às métricas de galerias, clientes, imports e armazenamento

#### Scenario: Upload ou lote sem saldo suficiente

- **WHEN** a API recusa a reserva de créditos por saldo insuficiente para a operação ou lote
- **THEN** o painel informa a insuficiência sem aceitar bytes nem permitir ao frontend substituir a decisão do servidor

#### Scenario: Consulta da carteira indisponível

- **WHEN** a consulta financeira falha enquanto os dados operacionais do dashboard foram carregados
- **THEN** o painel informa que o saldo está indisponível, preserva as métricas operacionais e não exibe zero como se fosse o saldo confirmado
