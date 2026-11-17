# Spec Delta

## Purpose

Definir uma cópia externa cifrada do backup global no Google Workspace do proprietário e a validação de recuperação exigida antes de abrir o cadastro do SaaS a tenants.

## ADDED Requirements

### Requirement: Arquivo cifrado antes do envio

A integração SHALL enviar ao Workspace somente o artefato global já cifrado e autenticado. Dumps, configurações e dados em claro MUST NOT ser transmitidos ou gravados no destino.

#### Scenario: Cópia externa solicitada
- **WHEN** o worker envia um backup global ao Workspace
- **THEN** o conteúdo recebido contém apenas o artefato cifrado, sem dump ou configuração em claro

### Requirement: Destino dedicado e privado

A cópia SHALL usar uma pasta dedicada autorizada na identidade Workspace configurada para o backup. O ensaio de recuperação pré-abertura SHALL usar a conta do proprietário; a rotina recorrente SHALL usar identidade Workspace dedicada e independente. O sistema MUST NOT criar permissões públicas ou ampliar permissões do Drive.

#### Scenario: Destino configurado
- **WHEN** o proprietário configura o destino da cópia
- **THEN** o sistema valida a pasta autorizada e mantém o acesso restrito às permissões herdadas, sem criar link público

#### Scenario: Identidades separadas
- **WHEN** o operador prepara o ensaio pré-abertura e a rotina recorrente
- **THEN** o ensaio usa a conta do proprietário e a rotina usa a identidade dedicada, cada qual com pasta e autorização verificadas; os segredos não são compartilhados nem registrados no catálogo

### Requirement: Busca delimitada e completa
A busca de objetos remotos SHALL limitar-se à pasta configurada, usando o escopo do usuário ou o `driveId` exato do Shared Drive. Busca incompleta, paginação inesperada, objeto duplicado ou metadata incompatível MUST falhar fechado antes de ler ou enviar o objeto.

#### Scenario: Busca de Shared Drive
- **WHEN** o destino é configurado em um Shared Drive específico
- **THEN** a busca usa somente o `driveId` configurado e rejeita resultado incompleto ou ambíguo

### Requirement: Acesso OAuth mínimo e protegido

O sistema SHALL usar `drive.file` quando a pasta dedicada for criada pelo aplicativo e a operação puder ser concluída com esse escopo. Escopos mais amplos MUST NOT ser solicitados sem decisão e revisão específicas. Refresh token e credenciais SHALL permanecer em configuração segura ou envelope cifrado; segredos MUST NOT aparecer em resposta, frontend, log, auditoria ou metadados do arquivo.

#### Scenario: Falha de autorização
- **WHEN** OAuth expira, é revogado ou não pode ser descriptografado
- **THEN** o estado fica indisponível/desconhecido com erro sanitizado, sem alterar a origem nem promover a cópia a verificada

### Requirement: Concessão OAuth exata

O callback SHALL aceitar somente o conjunto de escopos `{drive.file}`. Escopo ausente ou adicional MUST falhar fechado antes de persistir a conexão.

#### Scenario: Concessão com escopo adicional
- **WHEN** a resposta OAuth inclui `drive.file` junto de qualquer outro escopo
- **THEN** o callback rejeita a conexão e não persiste o refresh token

### Requirement: Conexão OAuth owner-only

O provider SHALL carregar somente conexão ativa do proprietário no tenant esperado, validar estado e escopo persistido exato, e descriptografar o refresh token pelo contexto tenant/credencial.

#### Scenario: Conexão ausente, revogada ou com escopo inesperado
- **WHEN** o provider interno não encontra conexão válida do tenant ou detecta estado/escopo divergente
- **THEN** não faz troca de token nem chamada Drive e retorna falha sanitizada de autorização

### Requirement: Access token efêmero

O provider SHALL trocar o refresh token por access token somente via transporte injetado. Não SHALL persistir nem registrar o access token; escopo retornado deve ser exatamente `drive.file`.

#### Scenario: Credencial efêmera para cópia interna
- **WHEN** o caller interno solicita credencial para cópia Workspace
- **THEN** o provider troca o refresh token cifrado e mantém o access token em memória durante a operação

#### Scenario: Renovação omite escopo inalterado
- **WHEN** o provider recebe resposta de refresh sem o campo `scope`
- **THEN** usa somente a autorização já registrada como exatamente `drive.file`; qualquer escopo adicional informado é rejeitado

### Requirement: Transporte privado e explícito

O provider MUST NOT criar transporte de rede implícito nem aceitar credenciais por request público.

#### Scenario: Transporte ausente
- **WHEN** o caller interno não fornece transporte OAuth ou Drive
- **THEN** a criação do store falha antes de consultar ou trocar a conexão

#### Scenario: Escopo mínimo insuficiente
- **WHEN** a pasta escolhida não estiver acessível com o escopo configurado
- **THEN** a integração falha fechada e solicita configuração válida; ela MUST NOT pedir silenciosamente um escopo mais amplo nem criar compartilhamento público

### Requirement: Reenvio idempotente

Cada objeto remoto SHALL ser vinculado ao UUID estável do backup global. Retry do mesmo objeto MUST NOT criar uma cópia concorrente considerada válida; conflito de conteúdo, pasta ou metadata SHALL falhar fechado.

#### Scenario: Retry após resposta perdida
- **WHEN** a API remota concluiu um upload, mas a aplicação não recebeu a confirmação
- **THEN** o retry localiza e valida o objeto do mesmo UUID antes de criar novo arquivo; divergência ou ambiguidade não é promovida a cópia verificada

### Requirement: Cópia remota verificada

O sistema MUST NOT considerar recuperável um upload sem leitura de retorno e validação criptográfica do mesmo artefato e contexto.

#### Scenario: Upload remoto concluído
- **WHEN** o Drive confirma o upload
- **THEN** o sistema lê o objeto pelo identificador privado, compara tamanho e SHA-256 do ciphertext e valida GCM, manifesto e schema antes de registrar a cópia como verificada

### Requirement: Restore Workspace antes da abertura a tenants

O cadastro público SHALL permanecer fechado até um teste autorizado com a conta do proprietário comprovar backup no Workspace e restore global em destino descartável isolado e vazio, e a rotina recorrente com identidade dedicada comprovar uma cópia lida de volta e validada.

#### Scenario: Tentativa de abrir cadastro sem prova
- **WHEN** o operador prepara a abertura do SaaS e não existe evidência válida do teste de restore Workspace
- **THEN** o release mantém o cadastro de tenants fechado e informa os gates de restore e identidade recorrente pendentes

#### Scenario: Restore pré-abertura comprovado
- **WHEN** o proprietário conclui o teste autorizado e o destino isolado passa nas verificações de integridade/schema
- **THEN** a evidência registra identidade/escopo/instante/resultado sem segredo e o gate de backup deixa de bloquear a abertura
