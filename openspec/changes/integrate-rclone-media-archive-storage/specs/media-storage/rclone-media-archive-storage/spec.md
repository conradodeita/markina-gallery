# Spec Delta

## Purpose

Definir o comportamento seguro e compatível de um provider Rclone crypt para armazenar e recuperar objetos de arquivo frio, usando o catálogo e o fluxo de recuperação existentes do produto.

## ADDED Requirements

### Requirement: Provider Rclone respeita o contrato de armazenamento de mídia

O provider Rclone SHALL implementar o contrato existente de armazenamento de arquivo frio sem criar fila, catálogo, manifesto de ciclo, API, interface ou ledger próprios. SHALL preservar upload idempotente por chave opaca, leitura de metadados, download verificado e exclusão idempotente por objeto.

#### Scenario: Executor usa o provider configurado

- **WHEN** o executor existente recebe explicitamente o provider Rclone para um tenant autorizado
- **THEN** arquivo, readback, recuperação, retry, lease e débito/liberação de créditos seguem os mesmos contratos e registros já usados pelo arquivo frio
- **AND** o provider não altera prazo, taxa, elegibilidade, reserva, auditoria ou política de retenção

### Requirement: Binding de tenant não substitui identidade persistida do provider

O provider Rclone SHALL permanecer inativo até aprovação do roteamento de objetos existentes e novos. Como leitura/exclusão recebe somente `remote_id`, o executor usa um storage por operação e o manifesto v1 omite provider, binding tenant→provider MUST NOT rotear objetos catalogados. Granularidade objeto/ciclo, default legado e evolução de catálogo/manifesto seguem sem decisão; esta proposta não escolhe migration.

#### Scenario: Provider alternativo encontra objeto legado sem discriminador

- **WHEN** uma operação de leitura ou exclusão recebe ID opaco catalogado antes da seleção de Rclone e não há associação de provider aprovada
- **THEN** nenhum fallback ou roteamento inferido por tenant ocorre e a operação de transição permanece bloqueada até haver mapeamento compatível revisado

### Requirement: Chaves e objetos mantêm isolamento por tenant

O provider SHALL aceitar somente chaves de objeto canônicas do catálogo e SHALL limitar cada operação ao namespace privado e ao tenant para os quais foi construído. O caminho remoto SHALL derivar exclusivamente dos UUIDs de tenant, galeria, pasta, ciclo e objeto. Nomes de clientes, telefones, nomes de arquivos de origem, URLs públicas ou outros dados pessoais MUST NOT compor nomes, comandos ou registros remotos.

#### Scenario: Objeto pertence ao tenant configurado

- **WHEN** uma operação usa chave ou identificador de objeto pertencente ao tenant configurado e à raiz de mídia configurada
- **THEN** o provider opera somente no objeto exato correspondente e retorna um identificador opaco compatível com o contrato existente

#### Scenario: Chave, tenant, namespace ou raiz divergem

- **WHEN** uma chave, identificador, prefixo, raiz ou metadado não corresponde ao tenant e objeto autorizados
- **THEN** o provider falha com erro sanitizado antes de acessar ou alterar outro objeto

### Requirement: Transferências são limitadas e verificáveis

Upload e download SHALL transmitir dados em blocos limitados, SHALL NOT materializar o objeto inteiro em memória e MUST calcular tamanho e SHA-256 sobre os bytes efetivamente transmitidos. Sucesso SHALL depender da correspondência entre tamanho/hash esperados e observados; o executor existente permanece responsável pelo readback integral antes de promover arquivo, recuperação ou débito.

#### Scenario: Upload e download íntegros

- **WHEN** o provider transfere um objeto cujo tamanho e SHA-256 correspondem ao catálogo
- **THEN** retorna metadados/recibo compatíveis com o contrato e o executor consegue confirmar readback integral sem carregar o objeto inteiro em memória

#### Scenario: Transferência truncada, excedente ou divergente

- **WHEN** tamanho, SHA-256, MIME ou metadados retornados divergem do valor esperado ou dos limites suportados
- **THEN** a operação falha de modo sanitizado e o executor não promove sucesso, não torna bytes parciais visíveis e não debita créditos

### Requirement: Metadados de objeto preservam MIME confiável

`read_object(remote_id)` SHALL retornar o MIME associado de forma durável e verificável ao objeto remoto, junto de seu tamanho e identidade. O executor SHALL comparar o MIME retornado com o MIME do catálogo antes de aceitar readback ou recuperação. O provider MUST NOT inferir MIME a partir de nome fornecido pelo usuário, extensão não confiável ou valor padrão; metadado ausente, inválido ou divergente MUST falhar fechado.

#### Scenario: MIME do objeto corresponde ao catálogo

- **WHEN** `read_object` resolve o ID remoto único e retorna metadado válido associado ao objeto
- **THEN** o executor compara esse MIME com o catálogo e prossegue somente se os valores forem iguais

#### Scenario: MIME não pode ser provado

- **WHEN** o backend/provider não consegue recuperar MIME durável associado ao ID ou ele diverge do catálogo
- **THEN** a operação falha de forma sanitizada antes de promover readback/recuperação ou debitar créditos

### Requirement: Repetição, ausência e exclusão falham fechadas

O provider SHALL reconhecer repetição da mesma chave quando o objeto existente tiver conteúdo e metadados compatíveis, e SHALL recusar conteúdo divergente sem sobrescrever. Somente uma consulta completa, válida e não ambígua pode comprovar ausência. A exclusão SHALL atingir somente o objeto exato validado; MUST NOT usar remoção recursiva nem tratar falha de consulta como ausência.

#### Scenario: Retry encontra objeto idêntico

- **WHEN** uma tentativa anterior deixou objeto íntegro e a mesma operação é repetida
- **THEN** o provider valida o objeto existente e retorna seu identificador sem criar duplicata ou sobrescrever bytes

#### Scenario: Busca falha ou retorna resultado ambíguo

- **WHEN** subprocesso, configuração, listagem, JSON, metadados, paginação, duplicidade ou caminho retornado forem inválidos/incompletos
- **THEN** o provider retorna erro sanitizado, não registra ausência e não autoriza upload, ownership ou exclusão com base nessa resposta

#### Scenario: Exclusão idempotente de objeto conhecido

- **WHEN** o executor solicita exclusão de identificador já validado no catálogo
- **THEN** o provider remove somente o objeto exato, aceita ausência comprovada como sucesso idempotente e preserva todos os demais objetos e namespaces

### Requirement: Configuração e comandos não podem redirecionar operações

O provider SHALL aceitar somente configuração validada e explicitamente injetada para um remote crypt e sua base autorizada. Deve executar operações de vocabulário fixo, sem shell arbitrário, sem overrides ambientais não revisados e sem aceitar caminhos de destino fornecidos por usuário/tenant. Credenciais, chaves, configuração, caminhos locais e saída bruta MUST NOT aparecer em logs ou erros.

#### Scenario: Configuração válida e comando permitido

- **WHEN** a composição recebe configuração validada para o namespace de mídia e uma operação suportada
- **THEN** executa somente o comando fixo correspondente, com a configuração previamente validada e sem expor valores sensíveis

#### Scenario: Configuração ausente, inválida ou redirecionada

- **WHEN** remote, base, raiz, arquivo de configuração, chave, permissão ou variável de override divergem da configuração permitida
- **THEN** o provider recusa antes de executar subprocesso ou consultar a fila, com erro estático sanitizado

### Requirement: Provider não é selecionado automaticamente

O provider SHALL permanecer não configurado por padrão. A composição SHALL receber explicitamente um provider já aprovado e validado; configuração ausente, inválida ou ambígua MUST NOT selecionar Rclone, Google Drive ou um fallback automaticamente, nem permitir reivindicar operação com storage volátil.

#### Scenario: Runtime sem provider explícito

- **WHEN** o worker está habilitado sem provider durável explicitamente configurado e aprovado
- **THEN** falha fechado antes de consultar ou reivindicar operação, sem inicializar subprocesso ou realizar acesso externo

#### Scenario: Provider Rclone explicitamente configurado

- **WHEN** o provider está injetado por composição aprovada e sua configuração passa todas as validações
- **THEN** somente operações cobertas por essa configuração podem ser reivindicadas e executadas, mantendo os gates de ambiente e autorização existentes

### Requirement: Composição e claim são limitados ao tenant com binding validado

A composição SHALL manter bindings validados entre tenant e provider durável. Novos claims e retomadas SHALL verificar o binding antes de gravar lease. O claim MUST preservar coordenador, lease e prioridade/FIFO no escopo habilitado. Após claim, o provider SHALL corresponder ao tenant da operação.

#### Scenario: Claim de tenant vinculado

- **WHEN** há operações elegíveis de vários tenants e somente um possui binding durável válido
- **THEN** o claim pode selecionar apenas operação daquele tenant, preservando a prioridade/FIFO entre candidatos elegíveis, e o executor recebe seu provider correspondente, mantendo a coordenação global

#### Scenario: Tenant sem binding tem operação enfileirada

- **WHEN** existe operação de tenant sem provider validado antes da seleção
- **THEN** ela não recebe novo lease e não inicia chamada externa; operações de tenants vinculados podem continuar respeitando a prioridade/FIFO dentro do conjunto habilitado

#### Scenario: Lease expirado pertence a tenant sem binding

- **WHEN** a operação no lease global expirado pertence a tenant que não está no conjunto de bindings válidos
- **THEN** o worker não reivindica nem redireciona esse lease e preserva o coordenador global sem liberá-lo por suposição
- **AND** outro tenant não recebe um claim concorrente enquanto esse lease permanecer ativo na coordenação global
- **AND** o worker emite aviso sanitizado com código estável que identifica o bloqueio operacional, sem registrar segredo/configuração

### Requirement: Retry interno do provider não repete a operação do worker

Retry finito de subprocesso/transferência SHALL permanecer dentro da operação e do lease atuais. MUST NOT criar nova operação, claim ou retry automático do ciclo. Falha comprovada segue o tratamento existente. Resultado incerto após efeito remoto possível mantém a reserva em `reconciliation_required`, sem replay automático.

#### Scenario: Retry interno seguro e finito

- **WHEN** um comando idempotente pode ser repetido com segurança e ainda há tentativas internas dentro do limite validado
- **THEN** o provider repete somente a transferência do objeto na mesma operação/lease, sem incrementar a tentativa do worker nem liberar/substituir o lease

#### Scenario: Falha interna comprovada após esgotar tentativas

- **WHEN** as tentativas finitas terminam e a falha externa é comprovada
- **THEN** o executor encaminha a falha comprovada ao estado/transição existente, sem criar novo claim ou repetir automaticamente a operação inteira
- **AND** a reserva só é liberada quando a falha sem restauração estiver comprovada

#### Scenario: Resultado externo incerto

- **WHEN** houve efeito remoto possível e o provider não consegue provar sucesso ou ausência
- **THEN** não repete automaticamente o subprocesso nem a operação e mantém a reserva em `reconciliation_required`
- **AND** esta proposta não adiciona ação/API de resolução; o endpoint de retry atual aceita somente operação `failed` e não resolve `reconciliation_required`

### Requirement: Limites de transferência e processo são finitos e validados

O provider SHALL validar limites finitos de bloco, tamanho de objeto, timeout e tentativas antes de transferir. MUST NOT usar leitura, timeout ou retry sem limite. Valores específicos SHALL ser justificados por caracterização sintética antes da implementação; sem limites válidos, falha antes de iniciar processo.

#### Scenario: Limites válidos e configurados

- **WHEN** composição recebe limites finitos validados e a operação usa stream dentro deles
- **THEN** a transferência permanece limitada em memória/tempo/tentativas e registra integridade do fluxo
- **AND** o bloco de 1 MiB usado pelo executor e pelo adapter Drive serve como baseline observável da aplicação, sem fixar limites totais ou de processo do Rclone

#### Scenario: Limite ausente ou excedido

- **WHEN** limite necessário está ausente/não finito ou tamanho, duração ou tentativas excedem o valor aprovado
- **THEN** o provider recusa ou interrompe de forma sanitizada, não promove conteúdo parcial e mantém o resultado em falha/reconciliação conforme a evidência disponível
