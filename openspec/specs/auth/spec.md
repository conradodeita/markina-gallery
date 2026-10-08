# auth Specification

## Purpose

Definir a autenticação unificada da Markina Gallery e a separação segura entre o fotógrafo administrador e clientes/responsáveis.

## Requirements

### Requirement: Tela única de entrada

O sistema SHALL disponibilizar uma única tela/rota de entrada para os contextos `Cliente` e `Fotógrafo`, com escolha explícita do contexto e campos correspondentes na mesma experiência visual.

#### Scenario: Seleção do contexto cliente

- **WHEN** o visitante escolhe `Cliente`
- **THEN** a tela apresenta nome completo e telefone, sem solicitar senha administrativa

#### Scenario: Seleção do contexto fotógrafo

- **WHEN** o visitante escolhe `Fotógrafo`
- **THEN** a tela apresenta e-mail e senha, sem solicitar nome de pessoa fotografada

### Requirement: OTP de cliente por WhatsApp

O sistema SHALL autenticar cliente/responsável mediante nome completo, telefone normalizado em E.164 e OTP de uso único enviado pelo adaptador WhatsApp.

#### Scenario: Cliente solicita código

- **WHEN** o cliente informa dados válidos e solicita entrada
- **THEN** o sistema cria desafio OTP com expiração curta, envia o código pelo WhatsApp e exibe a etapa de validação sem revelar se o telefone está cadastrado

#### Scenario: Cliente valida código

- **WHEN** o cliente informa o OTP correto dentro do prazo
- **THEN** o sistema invalida o desafio, cria sessão com papel `client` e encaminha o cliente conforme suas galerias autorizadas

#### Scenario: OTP inválido, usado ou expirado

- **WHEN** o cliente informa código inválido, já usado ou expirado
- **THEN** o sistema rejeita a autenticação, registra a tentativa, mantém resposta neutra e aplica rate limit

### Requirement: Autenticação forte do fotógrafo

O sistema SHALL autenticar o fotógrafo mediante e-mail verificado, senha válida e código TOTP válido de segundo fator.

#### Scenario: Senha válida exige TOTP

- **WHEN** o fotógrafo informa e-mail e senha corretos
- **THEN** o sistema solicita o código TOTP e não cria sessão administrativa antes da validação do segundo fator

#### Scenario: TOTP válido

- **WHEN** o fotógrafo informa TOTP válido dentro da janela aceita
- **THEN** o sistema cria sessão com papel `admin` e redireciona para a área administrativa

#### Scenario: Falha de senha ou TOTP

- **WHEN** a senha ou o TOTP são inválidos
- **THEN** o sistema rejeita o acesso, registra a tentativa, aplica rate limit e não revela qual fator falhou de maneira enumerável

### Requirement: Roteamento por papel e autorização

O backend SHALL determinar o destino e autorizar cada rota usando o papel e as relações persistidas da sessão, nunca somente dados enviados pelo frontend.

#### Scenario: Administrador acessa rota administrativa

- **WHEN** uma sessão `admin` acessa `/admin`
- **THEN** o sistema permite a entrada na área administrativa

#### Scenario: Cliente acessa galeria única

- **WHEN** uma sessão `client` possui uma única galeria autorizada
- **THEN** o sistema redireciona o cliente diretamente para essa galeria

#### Scenario: Cliente possui várias galerias

- **WHEN** uma sessão `client` possui duas ou mais galerias autorizadas
- **THEN** o sistema redireciona o cliente para sua biblioteca para escolher a galeria

#### Scenario: Papel incompatível

- **WHEN** uma sessão `client` tenta acessar `/admin` ou uma galeria sem autorização
- **THEN** o sistema responde com acesso negado sem revelar a existência do recurso e registra o evento

### Requirement: Identificação visível da sessão autenticada

O sistema SHALL apresentar nas áreas autenticadas do fotógrafo e da cliente a identidade associada à sessão validada pelo backend, sem aceitar essa identidade do navegador.

#### Scenario: Sessão do fotógrafo

- **WHEN** o fotógrafo abre uma tela autenticada da área administrativa
- **THEN** o cabeçalho apresenta `Logado como: [e-mail da conta autenticada]`

#### Scenario: Sessão da cliente

- **WHEN** a cliente abre uma tela autenticada da biblioteca ou de uma galeria
- **THEN** o cabeçalho apresenta `Logado como: [telefone E.164 ativo e verificado da cliente autenticada]`

#### Scenario: Identidade indisponível

- **WHEN** a consulta autenticada de identidade falha ou não retorna sujeito válido
- **THEN** o sistema não inventa nem reutiliza uma identidade anterior e mantém a área utilizável conforme a autorização existente

### Requirement: Contexto administrativo vinculado à conta do fotógrafo

O backend SHALL resolver o contexto do fotógrafo a partir da sessão administrativa persistida e de um vínculo ativo com a conta única da instalação, revalidando esse vínculo nas operações protegidas. O sistema MUST preservar os fatores de autenticação existentes e não usar identificadores enviados pelo frontend como autoridade para escolher a conta.

#### Scenario: Administrador legado vinculado
- **WHEN** o administrador atual, migrado com vínculo ativo, conclui senha e TOTP
- **THEN** sua sessão permite a operação na conta única do fotógrafo sem exigir novo cadastro

#### Scenario: Vínculo revogado após login
- **WHEN** o vínculo administrativo é desativado enquanto a sessão ainda é válida
- **THEN** a próxima operação protegida é recusada sem expor recursos da conta

#### Scenario: Tentativa de impor proprietário
- **WHEN** uma requisição administrativa inclui outro identificador de conta na URL, corpo ou cabeçalho
- **THEN** esse identificador não substitui o contexto autorizado e não permite leitura, alteração ou criação para outra conta

#### Scenario: Sessão sem vínculo
- **WHEN** uma sessão administrativa válida não possui vínculo ativo com a conta única
- **THEN** a operação protegida é recusada sem fallback para a primeira conta encontrada

### Requirement: Reautenticação OTP contextual a uma galeria autorizada

Cliente sem sessão SHALL poder solicitar OTP no contexto de uma galeria identificada internamente, desde que já possua vínculo ativo com ela. O identificador da galeria MUST NOT conceder acesso; o vínculo SHALL ser revalidado antes de enviar/re-enviar OTP e antes de criar a sessão.

#### Scenario: Cliente autorizado retoma pelo link da notificação

- **WHEN** o cliente informa nome e telefone na entrada contextual da galeria e possui vínculo ativo com ela
- **THEN** o sistema envia OTP pelo WhatsApp, cria sessão somente após validar o código e retorna à galeria solicitada

#### Scenario: Telefone sem vínculo ativo solicita reautenticação

- **WHEN** um visitante informa telefone sem vínculo ativo com a galeria indicada
- **THEN** o sistema mantém resposta externa neutra, não envia OTP e não concede sessão ou cadastro por esse contexto

#### Scenario: Vínculo revogado durante o desafio

- **WHEN** o vínculo com a galeria deixa de estar ativo antes do reenvio ou validação do OTP
- **THEN** o sistema não entrega novo código e recusa a sessão contextual sem revelar dados da galeria ou cliente
